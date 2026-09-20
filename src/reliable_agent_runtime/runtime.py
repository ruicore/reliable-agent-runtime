"""R1 application service for the deterministic model-tool vertical slice."""

from __future__ import annotations

from uuid import uuid4

from .domain import (
    ActionRecord,
    ActionResultState,
    ApprovalRequired,
    ApprovalState,
    AttemptRecord,
    BudgetState,
    CancellationAccepted,
    CancellationState,
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
from .recovery import (
    AdapterGuarantees,
    HumanDecisionKind,
    IncompatibleRecoveryMaterial,
    RecoveryDecision,
    RecoveryDecisionKind,
    RecoveryMaterial,
    RecoveryMaterialRequired,
    RecoveryOutcome,
    RecoveryPolicy,
)


class RuntimeService:
    """Minimal R1 submit/query/approve/execute/report surface.

    Recovery is explicit and guarantee-bound in Stage 02; cancellation, complete
    execution budgets and real providers remain unsupported in this slice.
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

    def configure_budgets(
        self,
        *,
        run_id: str,
        max_attempts: int | None,
        max_execution_seconds: float | None,
    ) -> BudgetState:
        self.repository.configure_budgets(run_id, max_attempts, max_execution_seconds)
        return self.repository.budget_state(run_id)

    def budget_state(self, run_id: str) -> BudgetState:
        return self.repository.budget_state(run_id)

    def record_human_wait(self, *, run_id: str, seconds: float) -> BudgetState:
        view = self.repository.get_view(run_id)
        self.repository.record_human_wait(
            run_id,
            seconds,
            self._event(run_id, "human_wait_recorded", len(view.events) + 1),
        )
        return self.repository.budget_state(run_id)

    def request_cancel(self, run_id: str):
        view = self.repository.get_view(run_id)
        self.repository.request_cancel(
            run_id,
            self._event(run_id, "cancellation_requested", len(view.events) + 1),
        )
        return self.repository.get_view(run_id)

    def accept_cancel(self, run_id: str):
        view = self.repository.get_view(run_id)
        self.repository.accept_cancel(
            run_id,
            self._event(run_id, "cancellation_accepted", len(view.events) + 1),
        )
        return self.repository.get_view(run_id)

    def confirm_stopped(self, run_id: str):
        view = self.repository.get_view(run_id)
        self.repository.confirm_stopped(
            run_id,
            self._event(run_id, "stopping_confirmed", len(view.events) + 1),
        )
        return self.repository.get_view(run_id)

    def invalidate_approval(self, *, run_id: str, reason: str):
        view = self.repository.get_view(run_id)
        if not view.action:
            return view
        normalized = canonicalize_input(reason)
        if not normalized:
            raise ValueError("approval invalidation reason is required")
        self.repository.invalidate_approval(
            view.action.action_id,
            self._event(
                run_id,
                "approval_invalidated",
                len(view.events) + 1,
                detail_digest=digest_text(normalized),
            ),
        )
        return self.repository.get_view(run_id)

    def execute(self, *, run_id: str):
        return self._dispatch(run_id=run_id, allow_unknown=False, event_prefix="dispatch")

    def _dispatch(self, *, run_id: str, allow_unknown: bool, event_prefix: str):
        view = self.repository.get_view(run_id)
        if not view.action:
            return view
        if view.run.state is RunState.TERMINATED:
            return view
        if view.action.cancellation in (
            CancellationState.ACCEPTED,
            CancellationState.STOP_CONFIRMED,
        ):
            return view
        if view.action.approval is not ApprovalState.APPROVED:
            raise ApprovalRequired("exact approval is required before dispatch")
        if view.action.result is not ActionResultState.NOT_STARTED and not (
            allow_unknown and view.action.result is ActionResultState.UNKNOWN
        ):
            return view

        attempt_id = uuid4().hex
        try:
            self.repository.prepare_attempt(
                attempt=AttemptRecord(
                    attempt_id,
                    view.action.action_id,
                    DispatchState.INTENT_PERSISTED,
                    ActionResultState.NOT_STARTED,
                ),
                event=self._event(run_id, f"{event_prefix}_attempt_intent_persisted", len(view.events) + 1),
            )
        except CancellationAccepted:
            return self.repository.get_view(run_id)
        # This durable transition is intentionally before the tool call.
        try:
            self.repository.mark_dispatched(
                view.action.action_id,
                attempt_id,
                self._event(run_id, f"{event_prefix}_recorded", len(view.events) + 2),
            )
        except CancellationAccepted:
            current = self.repository.get_view(run_id)
            self.repository.suppress_attempt(
                view.action.action_id,
                attempt_id,
                self._event(run_id, "dispatch_suppressed_by_cancellation", len(current.events) + 1),
            )
            return self.repository.get_view(run_id)
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
        current = self.repository.get_view(run_id)
        result_event = (
            "late_result_recorded"
            if current.action
            and current.action.cancellation in (CancellationState.ACCEPTED, CancellationState.STOP_CONFIRMED)
            else f"{event_prefix}_result_recorded"
        )
        self.repository.record_result(
            view.action.action_id,
            attempt_id,
            result,
            self._event(run_id, result_event, len(current.events) + 1),
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
            "cancellation": view.action.cancellation.value if view.action else None,
            "budget": {
                "max_attempts": view.budget.max_attempts,
                "attempts_consumed": view.budget.attempts_consumed,
                "max_execution_seconds": view.budget.max_execution_seconds,
                "execution_seconds_consumed": view.budget.execution_seconds_consumed,
                "human_wait_seconds": view.budget.human_wait_seconds,
            },
            "events": [event.kind for event in view.events],
            "limitations": [
                "recovery requires explicit adapter guarantees and material",
                "no automatic recovery scan",
                "no cancellation",
                "no complete execution-time budget",
                "no real providers",
            ],
        }

    def recovery_decision(
        self,
        *,
        run_id: str,
        guarantees: AdapterGuarantees,
        max_attempts: int | None,
    ) -> RecoveryDecision:
        """Return a conservative decision from durable facts without dispatching."""

        view = self.repository.get_view(run_id)
        if view.action is None:
            return RecoveryDecision(RecoveryDecisionKind.NO_ACTION, "run has no executable action")
        return RecoveryPolicy.decide(
            result=view.action.result,
            attempt_count=len(view.attempts),
            max_attempts=max_attempts,
            guarantees=guarantees,
        )

    def recover(
        self,
        *,
        run_id: str,
        guarantees: AdapterGuarantees,
        max_attempts: int | None,
        material: RecoveryMaterial | None,
    ) -> RecoveryOutcome:
        """Reconcile or retry only when the declared adapter contract permits it."""

        if material is None:
            raise RecoveryMaterialRequired("historical recovery material is required")
        view = self.repository.get_view(run_id)
        material.require_compatible(
            contract_version=view.run.contract_version,
            input_digest=view.run.input_digest,
        )
        decision = self.recovery_decision(
            run_id=run_id,
            guarantees=guarantees,
            max_attempts=max_attempts,
        )
        if decision.kind is RecoveryDecisionKind.QUERY:
            query = getattr(self.tool, "query", None)
            if not callable(query) or view.action is None or not view.attempts:
                return RecoveryOutcome(
                    RecoveryDecision(RecoveryDecisionKind.HUMAN_ATTENTION, "query guarantee has no query operation"),
                    view,
                )
            outcome = query(
                action_id=view.action.action_id,
                target=view.action.target,
                payload=view.action.payload,
            )
            queried_result = self._validated_tool_result(outcome)
            if queried_result in (ActionResultState.SUCCEEDED.value, ActionResultState.REJECTED.value):
                self.repository.record_result(
                    view.action.action_id,
                    view.attempts[-1].attempt_id,
                    queried_result,
                    self._event(run_id, "recovery_query_confirmed", len(view.events) + 1),
                )
                return RecoveryOutcome(decision, self.repository.get_view(run_id))
            self.repository.append_event(
                self._event(run_id, "recovery_query_unknown", len(view.events) + 1),
            )
            return RecoveryOutcome(
                RecoveryDecision(RecoveryDecisionKind.HUMAN_ATTENTION, "query did not verify completion"),
                self.repository.get_view(run_id),
            )
        if decision.kind is RecoveryDecisionKind.RETRY:
            return RecoveryOutcome(
                decision,
                self._dispatch(run_id=run_id, allow_unknown=True, event_prefix="recovery_retry"),
            )
        return RecoveryOutcome(decision, view)

    def handle_unknown(
        self,
        *,
        run_id: str,
        decision: HumanDecisionKind,
        rationale: str,
        material: RecoveryMaterial | None,
    ):
        """Record an evidence-bound human choice without rewriting the unknown fact."""

        if material is None:
            raise RecoveryMaterialRequired("historical recovery material is required")
        view = self.repository.get_view(run_id)
        material.require_compatible(
            contract_version=view.run.contract_version,
            input_digest=view.run.input_digest,
        )
        if not view.action or view.action.result is not ActionResultState.UNKNOWN:
            raise IncompatibleRecoveryMaterial("human handling requires an unknown action result")
        normalized = canonicalize_input(rationale)
        if not normalized:
            raise ValueError("human rationale is required")
        event = self._event(
            run_id,
            f"human_{decision.value}",
            len(view.events) + 1,
            detail_digest=digest_text(normalized),
        )
        if decision is HumanDecisionKind.TERMINATE:
            self.repository.append_event(event, state=RunState.TERMINATED)
            return self.repository.get_view(run_id)
        self.repository.append_event(event)
        if decision is HumanDecisionKind.AUTHORIZE_NEW_ATTEMPT:
            return self._dispatch(run_id=run_id, allow_unknown=True, event_prefix="human_authorized")
        return self.repository.get_view(run_id)

    @staticmethod
    def _validated_tool_result(outcome: object) -> str:
        if isinstance(outcome, ToolOutput) and outcome.contract_version == CONTRACT_VERSION:
            return outcome.result.value
        return ActionResultState.UNKNOWN.value

    @staticmethod
    def _event(
        run_id: str,
        kind: str,
        sequence: int,
        detail_digest: str | None = None,
    ) -> EventRecord:
        return EventRecord(uuid4().hex, run_id, kind, sequence, detail_digest)
