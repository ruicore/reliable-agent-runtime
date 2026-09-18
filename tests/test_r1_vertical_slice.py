from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Barrier

import pytest

from reliable_agent_runtime.domain import (
    ActionResultState,
    ModelInput,
    ModelValidity,
    RequestIdentityConflict,
    ToolOutput,
)
from reliable_agent_runtime.model import DeterministicModel, InvalidModel
from reliable_agent_runtime.recovery import (
    AdapterGuarantees,
    HumanDecisionKind,
    IncompatibleRecoveryMaterial,
    RecoveryDecisionKind,
    RecoveryMaterial,
    RecoveryMaterialRequired,
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


def test_recover_query_confirms_lost_reply_without_new_attempt() -> None:
    class LostReplyTool(SimulatedTool):
        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            super().execute(action_id=action_id, target=target, payload=payload)
            return {"reply": "lost"}

        def query(self, *, action_id: str, target: str, payload: str) -> ToolOutput:
            return ToolOutput(ActionResultState.SUCCEEDED)

    service, repository, _, observer = make_service()
    lost = LostReplyTool(observer._side_effects)
    service.tool = lost
    submitted = service.submit(request_id="req-query-reconcile", text="queryable side effect")
    assert submitted.action is not None
    service.approve(submitted.action.action_id)
    unknown = service.execute(run_id=submitted.run.run_id)
    outcome = service.recover(
        run_id=unknown.run.run_id,
        guarantees=AdapterGuarantees(queryable=True),
        max_attempts=3,
        material=RecoveryMaterial("r1", unknown.run.input_digest),
    )
    assert outcome.decision.kind is RecoveryDecisionKind.QUERY
    assert outcome.view.action is not None
    assert outcome.view.action.result is ActionResultState.SUCCEEDED
    assert len(outcome.view.attempts) == 1
    assert observer.count() == 1
    assert repository.get_view(unknown.run.run_id).action.result is ActionResultState.SUCCEEDED


def test_query_not_found_stays_unknown_and_moves_to_human_attention() -> None:
    class NotFoundTool(SimulatedTool):
        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            return {"reply": "lost"}

        def query(self, *, action_id: str, target: str, payload: str) -> ToolOutput:
            return ToolOutput(ActionResultState.UNKNOWN)

    service, _, _, _ = make_service()
    service.tool = NotFoundTool(SideEffectStore())
    submitted = service.submit(request_id="req-query-unknown", text="not found")
    assert submitted.action is not None
    service.approve(submitted.action.action_id)
    unknown = service.execute(run_id=submitted.run.run_id)
    outcome = service.recover(
        run_id=unknown.run.run_id,
        guarantees=AdapterGuarantees(queryable=True),
        max_attempts=3,
        material=RecoveryMaterial("r1", unknown.run.input_digest),
    )
    assert outcome.decision.kind is RecoveryDecisionKind.HUMAN_ATTENTION
    assert outcome.view.action is not None
    assert outcome.view.action.result is ActionResultState.UNKNOWN
    assert len(outcome.view.attempts) == 1


def test_verified_retry_creates_a_new_attempt_and_preserves_history() -> None:
    class RetryTool(SimulatedTool):
        def __init__(self, effects):
            super().__init__(effects)
            self.calls = 0

        def execute(self, *, action_id: str, target: str, payload: str) -> ToolOutput | object:
            self.calls += 1
            if self.calls == 1:
                return {"reply": "lost"}
            return super().execute(action_id=action_id, target=target, payload=payload)

    service, _, _, _ = make_service()
    effects = SideEffectStore()
    retry_tool = RetryTool(effects)
    service.tool = retry_tool
    submitted = service.submit(request_id="req-safe-retry", text="safe retry")
    assert submitted.action is not None
    service.approve(submitted.action.action_id)
    unknown = service.execute(run_id=submitted.run.run_id)
    guarantees = AdapterGuarantees(
        deduplication_verified=True,
        deduplication_scope="action",
        retry_safe=True,
    )
    outcome = service.recover(
        run_id=unknown.run.run_id,
        guarantees=guarantees,
        max_attempts=2,
        material=RecoveryMaterial("r1", unknown.run.input_digest),
    )
    assert outcome.decision.kind is RecoveryDecisionKind.RETRY
    assert outcome.view.action is not None
    assert outcome.view.action.result is ActionResultState.SUCCEEDED
    assert len(outcome.view.attempts) == 2
    assert effects.count() == 1


def test_human_handling_preserves_unknown_and_can_terminate_or_authorize() -> None:
    service, _, _, _ = make_service()
    service.tool = type("MalformedTool", (), {"execute": lambda *_args, **_kwargs: {"ack": "yes"}})()
    submitted = service.submit(request_id="req-human", text="human handling")
    assert submitted.action is not None
    service.approve(submitted.action.action_id)
    unknown = service.execute(run_id=submitted.run.run_id)
    material = RecoveryMaterial("r1", unknown.run.input_digest)

    confirmed = service.handle_unknown(
        run_id=unknown.run.run_id,
        decision=HumanDecisionKind.CONFIRM_EXTERNAL_COMPLETION,
        rationale="independent evidence reviewed",
        material=material,
    )
    assert confirmed.run.state.value == "ready"
    assert confirmed.action is not None
    assert confirmed.action.result is ActionResultState.UNKNOWN
    assert confirmed.events[-1].detail_digest is not None

    terminated = service.handle_unknown(
        run_id=unknown.run.run_id,
        decision=HumanDecisionKind.TERMINATE,
        rationale="operator stops unresolved work",
        material=material,
    )
    assert terminated.run.state.value == "terminated"
    assert terminated.action is not None
    assert terminated.action.result is ActionResultState.UNKNOWN

    class HumanAuthorizedTool:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            self.calls += 1
            return ToolOutput(ActionResultState.SUCCEEDED) if self.calls == 2 else {"ack": "yes"}

    authorized_tool = HumanAuthorizedTool()
    authorized_service, _, _, _ = make_service()
    authorized_service.tool = authorized_tool
    authorized = authorized_service.submit(request_id="req-human-authorized", text="explicit retry")
    assert authorized.action is not None
    authorized_service.approve(authorized.action.action_id)
    authorized_unknown = authorized_service.execute(run_id=authorized.run.run_id)
    authorized_result = authorized_service.handle_unknown(
        run_id=authorized_unknown.run.run_id,
        decision=HumanDecisionKind.AUTHORIZE_NEW_ATTEMPT,
        rationale="operator accepts a separately tracked risk",
        material=RecoveryMaterial("r1", authorized_unknown.run.input_digest),
    )
    assert authorized_result.action is not None
    assert authorized_result.action.result is ActionResultState.SUCCEEDED
    assert len(authorized_result.attempts) == 2


def test_missing_recovery_material_is_an_explicit_refusal() -> None:
    service, _, _, _ = make_service()
    with pytest.raises(RecoveryMaterialRequired):
        service.recover(
            run_id="missing",
            guarantees=AdapterGuarantees(),
            max_attempts=1,
            material=None,
        )


def test_real_process_restart_reconstructs_unknown_attempt_from_sqlite(tmp_path) -> None:
    database = tmp_path / "process-restart.sqlite"
    source_root = Path(__file__).parents[1] / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root) + os.pathsep + env.get("PYTHONPATH", "")
    writer = """
from reliable_agent_runtime import DeterministicModel, RuntimeService, SQLiteRepository
from reliable_agent_runtime.tool import SideEffectStore
import sys

class LostReplyTool:
    def execute(self, *, action_id: str, target: str, payload: str) -> object:
        return {"reply": "lost"}

database = sys.argv[1]
service = RuntimeService(SQLiteRepository(f"sqlite:///{database}"), DeterministicModel(), LostReplyTool())
view = service.submit(request_id="process-restart", text="durable unknown")
service.approve(view.action.action_id)
result = service.execute(run_id=view.run.run_id)
print(result.run.run_id)
"""
    first = subprocess.run(
        [sys.executable, "-c", writer, str(database)],
        cwd=Path(__file__).parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    run_id = first.stdout.strip()
    reader = """
from reliable_agent_runtime import DeterministicModel, RuntimeService, SQLiteRepository
import sys

class LostReplyTool:
    def execute(self, *, action_id: str, target: str, payload: str) -> object:
        return {"reply": "lost"}

database, run_id = sys.argv[1:]
service = RuntimeService(SQLiteRepository(f"sqlite:///{database}"), DeterministicModel(), LostReplyTool())
view = service.query(run_id)
print(len(view.attempts), view.action.result.value)
"""
    second = subprocess.run(
        [sys.executable, "-c", reader, str(database), run_id],
        cwd=Path(__file__).parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert second.stdout.strip() == "1 unknown"


def test_sqlite_event_schema_additive_migration_is_applied(tmp_path) -> None:
    database = tmp_path / "old-schema.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE events (event_id VARCHAR(64) PRIMARY KEY, run_id VARCHAR(64) NOT NULL, "
            "kind VARCHAR(128) NOT NULL, sequence INTEGER NOT NULL, created_at DATETIME NOT NULL)"
        )
        connection.commit()

    SQLiteRepository(f"sqlite:///{database}")
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(events)")}
    assert "detail_digest" in columns
