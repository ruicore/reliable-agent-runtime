"""R1 application service for the deterministic model-tool vertical slice."""

from __future__ import annotations

from uuid import uuid4

from .domain import (
    ActionRecord,
    ActionResultState,
    ApprovalRequired,
    ApprovalState,
    AttemptRecord,
    CONTRACT_VERSION,
    ConcurrentSubmission,
    DispatchState,
    EventRecord,
    InvalidModelOutput,
    ModelInput,
    ModelValidity,
    RequestIdentityConflict,
    RunRecord,
    RunState,
    ToolOutput,
    action_digest,
    canonical_payload,
    canonicalize_input,
    digest_text,
    safe_model_output,
)
from .ports import ModelPort, RuntimeRepository, ToolPort


class RuntimeService:
    """Minimal R1 submit/query/approve/execute/report surface.

    Recovery, retries, cancellation, budgets and real providers are deliberately
    unsupported in this slice and are not silently inferred.
    """

    def __init__(self, repository: RuntimeRepository, model: ModelPort, tool: ToolPort) -> None:
        self.repository = repository
        self.model = model
        self.tool = tool

    def submit(self, *, request_id: str, text: str):
        canonical = canonicalize_input(text)
        input_digest = digest_text(canonical)
        existing = self.repository.find_by_request(request_id)
        if existing:
            if existing.run.input_digest != input_digest:
                raise RequestIdentityConflict("request identity is already bound to different content")
            return existing

        run_id = uuid4().hex
        try:
            output = safe_model_output(self.model.generate(ModelInput(canonical)))
        except InvalidModelOutput:
            run = RunRecord(run_id, request_id, input_digest, CONTRACT_VERSION, RunState.MODEL_INVALID)
            event = self._event(run_id, "model_output_invalid", 1)
            try:
                self.repository.persist_submission(run, None, [event])
            except ConcurrentSubmission as concurrent:
                if concurrent.existing.run.input_digest != input_digest:
                    raise RequestIdentityConflict("request identity is already bound to different canonical content") from concurrent
                return concurrent.existing
            return self.repository.get_view(run_id)

        if output.validity is ModelValidity.INVALID:
            run = RunRecord(run_id, request_id, input_digest, CONTRACT_VERSION, RunState.MODEL_INVALID)
            event = self._event(run_id, "model_output_invalid", 1)
            try:
                self.repository.persist_submission(run, None, [event])
            except ConcurrentSubmission as concurrent:
                if concurrent.existing.run.input_digest != input_digest:
                    raise RequestIdentityConflict("request identity is already bound to different canonical content") from concurrent
                return concurrent.existing
            return self.repository.get_view(run_id)

        payload = canonical_payload(output.title, output.body)
        action_id = uuid4().hex
        action = ActionRecord(
            action_id=action_id,
            run_id=run_id,
            target="practice_card_store",
            payload=payload,
            action_digest=action_digest(target="practice_card_store", payload=payload),
            approval=ApprovalState.PENDING,
            dispatch=DispatchState.NOT_DISPATCHED,
            result=ActionResultState.NOT_STARTED,
        )
        run = RunRecord(run_id, request_id, input_digest, CONTRACT_VERSION, RunState.PENDING_APPROVAL)
        try:
            self.repository.persist_submission(
                run,
                action,
                [self._event(run_id, "run_created", 1), self._event(run_id, "action_intent_persisted", 2)],
            )
        except ConcurrentSubmission as concurrent:
            if concurrent.existing.run.input_digest != input_digest:
                raise RequestIdentityConflict("request identity is already bound to different canonical content") from concurrent
            return concurrent.existing
        return self.repository.get_view(run_id)

    def query(self, run_id: str):
        return self.repository.get_view(run_id)

    def approve(self, action_id: str):
        self.repository.approve(action_id)

    def execute(self, *, run_id: str):
        view = self.repository.get_view(run_id)
        if not view.action:
            return view
        if view.action.approval is not ApprovalState.APPROVED:
            raise ApprovalRequired("exact approval is required before dispatch")
        if view.action.result is not ActionResultState.NOT_STARTED:
            return view

        attempt_id = uuid4().hex
        self.repository.create_attempt(
            attempt=AttemptRecord(attempt_id, view.action.action_id, DispatchState.INTENT_PERSISTED, ActionResultState.NOT_STARTED),
            event=self._event(run_id, "attempt_intent_persisted", len(view.events) + 1),
        )
        # This durable transition is intentionally before the tool call.
        self.repository.mark_dispatched(
            view.action.action_id,
            attempt_id,
            self._event(run_id, "dispatch_recorded", len(view.events) + 2),
        )
        outcome = self.tool.execute(
            action_id=view.action.action_id,
            target=view.action.target,
            payload=view.action.payload,
        )
        if isinstance(outcome, ToolOutput) and outcome.contract_version == CONTRACT_VERSION:
            result = outcome.result.value
        elif outcome == "completed":  # compatibility for a minimal test adapter
            result = ActionResultState.SUCCEEDED.value
        else:
            # A malformed acknowledgement cannot prove completion and is not retried.
            result = ActionResultState.UNKNOWN.value
        self.repository.record_result(
            view.action.action_id,
            attempt_id,
            result,
            self._event(run_id, "result_recorded", len(view.events) + 3),
        )
        return self.repository.get_view(run_id)

    def report(self, run_id: str) -> dict[str, object]:
        view = self.repository.get_view(run_id)
        return {
            "contract_version": CONTRACT_VERSION,
            "run_id": view.run.run_id,
            "request_id": view.run.request_id,
            "run_state": view.run.state.value,
            "action_id": view.action.action_id if view.action else None,
            "action_result": view.action.result.value if view.action else None,
            "attempt_count": len(view.attempts),
            "events": [event.kind for event in view.events],
            "limitations": ["no retries", "no cancellation", "no recovery", "no real providers"],
        }

    @staticmethod
    def _event(run_id: str, kind: str, sequence: int) -> EventRecord:
        return EventRecord(uuid4().hex, run_id, kind, sequence)
