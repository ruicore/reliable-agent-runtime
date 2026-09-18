from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from reliable_agent_runtime.domain import (
    ActionResultState,
    ModelInput,
    ModelValidity,
    RequestIdentityConflict,
)
from reliable_agent_runtime.model import DeterministicModel, InvalidModel
from reliable_agent_runtime.recovery import (
    AdapterGuarantees,
    IncompatibleRecoveryMaterial,
    RecoveryDecisionKind,
    RecoveryMaterial,
)
from reliable_agent_runtime.runtime import RuntimeService
from reliable_agent_runtime.sqlite import SQLiteRepository
from reliable_agent_runtime.tool import IndependentObserver, SideEffectStore, SimulatedTool


def make_service(model=None):
    repository = SQLiteRepository()
    effects = SideEffectStore()
    tool = SimulatedTool(effects)
    service = RuntimeService(repository, model or DeterministicModel(), tool)
    return service, repository, tool, IndependentObserver(effects)


def test_deterministic_model_is_stable_for_valid_input() -> None:
    model = DeterministicModel()
    assert model.generate(ModelInput("  durable facts  ")) == model.generate(ModelInput("durable facts"))
    assert model.generate(ModelInput("durable facts")).validity is ModelValidity.VALID


def test_normal_execution_persists_before_dispatch_and_is_independently_observed() -> None:
    service, repository, tool, observer = make_service()
    submitted = service.submit(request_id="req-1", text="SQLite persistence")
    assert submitted.action is not None
    assert submitted.action.dispatch.value == "not_dispatched"
    service.approve(submitted.action.action_id)

    class ObservingTool(SimulatedTool):
        def execute(self, *, action_id: str, target: str, payload: str) -> str:
            before_call = repository.get_view(submitted.run.run_id)
            assert [event.kind for event in before_call.events][-1] == "dispatch_recorded"
            assert before_call.action is not None
            assert before_call.action.dispatch.value == "dispatched"
            return super().execute(action_id=action_id, target=target, payload=payload)

    # Replace only the adapter used by this service; Runtime still has no observer reference.
    service.tool = ObservingTool(tool._side_effects)
    completed = service.execute(run_id=submitted.run.run_id)
    assert completed.run.state.value == "completed"
    assert completed.action is not None
    assert completed.action.result.value == "succeeded"
    assert completed.action.dispatch.value == "dispatched"
    assert len(completed.attempts) == 1
    assert observer.find(completed.action.action_id) is not None
    assert tool.dispatch_count == 0
    assert service.report(completed.run.run_id)["attempt_count"] == 1


def test_duplicate_submission_reuses_one_logical_run_and_action() -> None:
    service, _, tool, observer = make_service()
    first = service.submit(request_id="req-duplicate", text="same content")
    second = service.submit(request_id="req-duplicate", text="  same   content ")
    assert second.run.run_id == first.run.run_id
    assert second.action is not None and first.action is not None
    assert second.action.action_id == first.action.action_id
    service.approve(first.action.action_id)
    service.execute(run_id=first.run.run_id)
    assert tool.dispatch_count == 1
    assert observer.count() == 1


def test_concurrent_duplicate_submission_resolves_to_one_logical_run() -> None:
    barrier = Barrier(2)

    class ConcurrentModel(DeterministicModel):
        def generate(self, model_input):
            barrier.wait(timeout=5)
            return super().generate(model_input)

    service, _, _, _ = make_service(ConcurrentModel())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(service.submit, request_id="req-concurrent", text="same content")
            for _ in range(2)
        ]
        results = [future.result(timeout=5) for future in futures]

    assert results[0].run.run_id == results[1].run.run_id
    assert results[0].action is not None and results[1].action is not None
    assert results[0].action.action_id == results[1].action.action_id


def test_request_identity_conflict_does_not_mutate_original() -> None:
    service, _, _, _ = make_service()
    original = service.submit(request_id="req-conflict", text="original")
    with pytest.raises(RequestIdentityConflict):
        service.submit(request_id="req-conflict", text="different")
    preserved = service.query(original.run.run_id)
    assert preserved.run.input_digest == original.run.input_digest
    assert [event.kind for event in preserved.events] == ["run_created", "action_intent_persisted"]


def test_invalid_model_output_creates_no_executable_action() -> None:
    invalid = InvalidModel("malformed")
    service, _, tool, observer = make_service(invalid)
    view = service.submit(request_id="req-invalid", text="some input")
    assert view.run.state.value == "model_invalid"
    assert view.action is None
    assert "model_output_invalid" in [event.kind for event in view.events]
    assert tool.dispatch_count == 0
    assert observer.count() == 0


def test_invalid_tool_response_is_unknown_and_not_success() -> None:
    class MalformedTool:
        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            return {"ack": "yes"}

    service, _, _, _ = make_service()
    service.tool = MalformedTool()
    view = service.submit(request_id="req-bad-tool", text="valid model input")
    assert view.action is not None
    service.approve(view.action.action_id)
    executed = service.execute(run_id=view.run.run_id)
    assert executed.action is not None
    assert executed.action.result is ActionResultState.UNKNOWN
    assert executed.run.state.value == "ready"


def test_unknown_without_verified_guarantees_requires_human_attention() -> None:
    class NonQueryableTool:
        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            return {"ack": "yes"}

    service, _, _, _ = make_service()
    service.tool = NonQueryableTool()
    view = service.submit(request_id="req-recovery-human", text="unknown result")
    assert view.action is not None
    service.approve(view.action.action_id)
    executed = service.execute(run_id=view.run.run_id)

    decision = service.recovery_decision(
        run_id=executed.run.run_id,
        guarantees=AdapterGuarantees(),
        max_attempts=3,
    )
    assert decision.kind is RecoveryDecisionKind.HUMAN_ATTENTION
    assert len(service.query(executed.run.run_id).attempts) == 1


def test_queryable_unknown_is_reconciled_before_retry() -> None:
    service, _, _, _ = make_service()
    view = service.submit(request_id="req-recovery-query", text="query result")
    assert view.action is not None
    service.approve(view.action.action_id)
    service.tool = type("MalformedTool", (), {"execute": lambda *_args, **_kwargs: {"ack": "yes"}})()
    executed = service.execute(run_id=view.run.run_id)

    decision = service.recovery_decision(
        run_id=executed.run.run_id,
        guarantees=AdapterGuarantees(queryable=True),
        max_attempts=3,
    )
    assert decision.kind is RecoveryDecisionKind.QUERY


def test_retry_requires_verified_deduplication_and_remaining_attempts() -> None:
    service, _, _, _ = make_service()
    view = service.submit(request_id="req-recovery-retry", text="retry result")
    assert view.action is not None
    service.approve(view.action.action_id)
    service.tool = type("MalformedTool", (), {"execute": lambda *_args, **_kwargs: {"ack": "yes"}})()
    executed = service.execute(run_id=view.run.run_id)

    guarantees = AdapterGuarantees(
        deduplication_verified=True,
        deduplication_scope="action",
        retry_safe=True,
    )
    decision = service.recovery_decision(
        run_id=executed.run.run_id,
        guarantees=guarantees,
        max_attempts=3,
    )
    assert decision.kind is RecoveryDecisionKind.RETRY
    exhausted = service.recovery_decision(
        run_id=executed.run.run_id,
        guarantees=guarantees,
        max_attempts=1,
    )
    assert exhausted.kind is RecoveryDecisionKind.HUMAN_ATTENTION


def test_recovery_material_rejects_incompatible_history() -> None:
    material = RecoveryMaterial(contract_version="r1", input_digest="a" * 64)
    with pytest.raises(IncompatibleRecoveryMaterial):
        material.require_compatible(contract_version="r1", input_digest="b" * 64)


def test_attempt_accounting_survives_new_runtime_instance(tmp_path) -> None:
    database = tmp_path / "runtime.sqlite"
    url = f"sqlite:///{database}"
    repository = SQLiteRepository(url)
    effects = SideEffectStore()
    service = RuntimeService(repository, DeterministicModel(), SimulatedTool(effects))
    view = service.submit(request_id="req-restart", text="durable attempt")
    assert view.action is not None
    service.approve(view.action.action_id)
    service.tool = type("MalformedTool", (), {"execute": lambda *_args, **_kwargs: {"ack": "yes"}})()
    executed = service.execute(run_id=view.run.run_id)

    restarted = RuntimeService(
        SQLiteRepository(url),
        DeterministicModel(),
        type("MalformedTool", (), {"execute": lambda *_args, **_kwargs: {"ack": "yes"}})(),
    )
    recovered_view = restarted.query(executed.run.run_id)
    assert len(recovered_view.attempts) == 1
    decision = restarted.recovery_decision(
        run_id=executed.run.run_id,
        guarantees=AdapterGuarantees(),
        max_attempts=3,
    )
    assert decision.kind is RecoveryDecisionKind.HUMAN_ATTENTION
