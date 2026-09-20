from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time

import pytest

from reliable_agent_runtime.domain import (
    ActionResultState,
    ApprovalRequired,
    BudgetExhausted,
    CancellationState,
    ToolOutput,
)
from reliable_agent_runtime.model import DeterministicModel
from reliable_agent_runtime.recovery import AdapterGuarantees, RecoveryMaterial
from reliable_agent_runtime.runtime import RuntimeService
from reliable_agent_runtime.sqlite import SQLiteRepository
from reliable_agent_runtime.tool import SideEffectStore, SimulatedTool


def make_service(*, repository: SQLiteRepository | None = None, tool=None):
    repository = repository or SQLiteRepository()
    tool = tool or SimulatedTool(SideEffectStore())
    return RuntimeService(repository, DeterministicModel(), tool), repository, tool


def approved_run(service: RuntimeService, request_id: str):
    view = service.submit(request_id=request_id, text="controlled execution")
    assert view.action is not None
    service.approve(view.action.action_id)
    return service.query(view.run.run_id)


def test_cancel_before_dispatch_blocks_tool_and_attempt_creation() -> None:
    service, _, tool = make_service()
    view = approved_run(service, "cancel-before-dispatch")

    requested = service.request_cancel(view.run.run_id)
    assert requested.action is not None
    assert requested.action.cancellation is CancellationState.REQUESTED
    accepted = service.accept_cancel(view.run.run_id)
    assert accepted.action is not None
    assert accepted.action.cancellation is CancellationState.ACCEPTED

    result = service.execute(run_id=view.run.run_id)
    assert result.run.state.value == "cancelled"
    assert len(result.attempts) == 0
    assert tool.dispatch_count == 0


def test_stop_confirmation_is_distinct_from_cancellation_acceptance() -> None:
    service, _, _ = make_service()
    view = approved_run(service, "stop-confirmation")
    service.request_cancel(view.run.run_id)
    accepted = service.accept_cancel(view.run.run_id)
    assert accepted.action is not None
    assert accepted.action.cancellation is CancellationState.ACCEPTED

    stopped = service.confirm_stopped(view.run.run_id)
    assert stopped.action is not None
    assert stopped.action.cancellation is CancellationState.STOP_CONFIRMED
    assert [event.kind for event in stopped.events][-3:] == [
        "cancellation_requested",
        "cancellation_accepted",
        "stopping_confirmed",
    ]


def test_cancel_during_dispatch_preserves_late_success_without_completing_run() -> None:
    started = Event()
    release = Event()

    class BlockingTool:
        def execute(self, *, action_id: str, target: str, payload: str) -> ToolOutput:
            started.set()
            assert release.wait(timeout=5)
            return ToolOutput(ActionResultState.SUCCEEDED)

    service, _, _ = make_service(tool=BlockingTool())
    view = approved_run(service, "cancel-during-dispatch")
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(service.execute, run_id=view.run.run_id)
        assert started.wait(timeout=5)
        service.request_cancel(view.run.run_id)
        service.accept_cancel(view.run.run_id)
        release.set()
        completed_call = future.result(timeout=5)

    assert completed_call.run.state.value == "cancelled"
    assert completed_call.action is not None
    assert completed_call.action.result is ActionResultState.SUCCEEDED
    assert "late_result_recorded" in [event.kind for event in completed_call.events]
    assert len(completed_call.attempts) == 1


def test_in_flight_attempt_blocks_concurrent_dispatch() -> None:
    started = Event()
    release = Event()

    class BlockingTool:
        def execute(self, *, action_id: str, target: str, payload: str) -> ToolOutput:
            started.set()
            assert release.wait(timeout=5)
            return ToolOutput(ActionResultState.SUCCEEDED)

    service, _, _ = make_service(tool=BlockingTool())
    view = approved_run(service, "concurrent-dispatch")
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(service.execute, run_id=view.run.run_id)
        assert started.wait(timeout=5)
        with pytest.raises(BudgetExhausted, match="in-flight"):
            service.execute(run_id=view.run.run_id)
        release.set()
        completed = future.result(timeout=5)

    assert len(completed.attempts) == 1


def test_approval_invalidation_survives_restart_and_blocks_dispatch(tmp_path) -> None:
    database = tmp_path / "approval.sqlite"
    url = f"sqlite:///{database}"
    service, _, tool = make_service(repository=SQLiteRepository(url))
    view = approved_run(service, "approval-invalidation")
    invalidated = service.invalidate_approval(
        run_id=view.run.run_id,
        reason="recovery material changed",
    )
    assert invalidated.action is not None
    assert invalidated.action.approval.value == "rejected"

    restarted, _, _ = make_service(repository=SQLiteRepository(url), tool=tool)
    with pytest.raises(ApprovalRequired):
        restarted.execute(run_id=view.run.run_id)
    assert restarted.query(view.run.run_id).attempts == ()
    assert tool.dispatch_count == 0


def test_retry_budget_is_persistent_and_blocks_new_attempts(tmp_path) -> None:
    class UnknownTool:
        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            return {"ack": "yes"}

    database = tmp_path / "retry-budget.sqlite"
    url = f"sqlite:///{database}"
    service, _, _ = make_service(repository=SQLiteRepository(url), tool=UnknownTool())
    view = approved_run(service, "retry-budget")
    service.configure_budgets(
        run_id=view.run.run_id,
        max_attempts=1,
        max_execution_seconds=30,
    )
    unknown = service.execute(run_id=view.run.run_id)
    assert unknown.action is not None
    assert unknown.action.result is ActionResultState.UNKNOWN

    restarted, _, _ = make_service(repository=SQLiteRepository(url), tool=UnknownTool())
    guarantees = AdapterGuarantees(
        deduplication_verified=True,
        deduplication_scope="action",
        retry_safe=True,
    )
    with pytest.raises(BudgetExhausted):
        restarted.recover(
            run_id=view.run.run_id,
            guarantees=guarantees,
            max_attempts=2,
            material=RecoveryMaterial("r1", view.run.input_digest),
        )
    budget = restarted.budget_state(view.run.run_id)
    assert budget.attempts_consumed == 1
    assert budget.max_attempts == 1


def test_execution_time_budget_blocks_retry_and_human_wait_is_separate() -> None:
    class SlowUnknownTool:
        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            time.sleep(0.02)
            return {"ack": "yes"}

    service, _, _ = make_service(tool=SlowUnknownTool())
    view = approved_run(service, "execution-budget")
    service.configure_budgets(
        run_id=view.run.run_id,
        max_attempts=3,
        max_execution_seconds=0.005,
    )
    unknown = service.execute(run_id=view.run.run_id)
    budget_before_wait = service.budget_state(view.run.run_id)
    assert budget_before_wait.execution_seconds_consumed >= 0.005
    assert budget_before_wait.human_wait_seconds == 0

    budget_after_wait = service.record_human_wait(run_id=view.run.run_id, seconds=7.5)
    assert budget_after_wait.human_wait_seconds == 7.5
    assert budget_after_wait.execution_seconds_consumed == pytest.approx(
        budget_before_wait.execution_seconds_consumed,
        rel=0.05,
    )

    guarantees = AdapterGuarantees(
        deduplication_verified=True,
        deduplication_scope="action",
        retry_safe=True,
    )
    with pytest.raises(BudgetExhausted):
        service.recover(
            run_id=unknown.run.run_id,
            guarantees=guarantees,
            max_attempts=3,
            material=RecoveryMaterial("r1", unknown.run.input_digest),
        )
