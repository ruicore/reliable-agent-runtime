"""Database-neutral ports used by the application layer."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol, Sequence

from .domain import (
    ActionRecord,
    AttemptRecord,
    EventRecord,
    RunRecord,
    RunState,
    RunView,
    BudgetState,
)


class RuntimeRepository(Protocol):
    """Durable facts required by the R1 application service.

    No ORM, SQL, or database-specific object crosses this boundary.
    """

    def find_by_request(self, request_id: str) -> RunView | None: ...

    def persist_submission(
        self,
        run: RunRecord,
        action: ActionRecord | None,
        events: Sequence[EventRecord],
    ) -> None: ...

    def get_view(self, run_id: str) -> RunView: ...

    def approve(self, action_id: str) -> None: ...

    def create_attempt(self, attempt: AttemptRecord, event: EventRecord) -> None: ...

    def mark_dispatched(self, action_id: str, attempt_id: str, event: EventRecord) -> None: ...

    def record_result(
        self,
        action_id: str,
        attempt_id: str,
        result: str,
        event: EventRecord,
    ) -> None: ...

    def append_event(self, event: EventRecord, state: RunState | None = None) -> None: ...

    def prepare_attempt(self, attempt: AttemptRecord, event: EventRecord) -> None: ...

    def suppress_attempt(
        self,
        action_id: str,
        attempt_id: str,
        event: EventRecord,
    ) -> None: ...

    def configure_budgets(
        self,
        run_id: str,
        max_attempts: int | None,
        max_execution_seconds: float | None,
    ) -> None: ...

    def budget_state(self, run_id: str) -> BudgetState: ...

    def record_human_wait(self, run_id: str, seconds: float, event: EventRecord) -> None: ...

    def request_cancel(self, run_id: str, event: EventRecord) -> None: ...

    def accept_cancel(self, run_id: str, event: EventRecord) -> None: ...

    def confirm_stopped(self, run_id: str, event: EventRecord) -> None: ...

    def invalidate_approval(self, action_id: str, event: EventRecord) -> None: ...


class ModelPort(Protocol):
    def generate(self, model_input: object) -> object: ...


class ToolPort(Protocol):
    def execute(self, *, action_id: str, target: str, payload: str) -> object: ...


class QueryableToolPort(ToolPort, Protocol):
    def query(self, *, action_id: str, target: str, payload: str) -> object: ...


class UnitOfWork(AbstractContextManager["UnitOfWork"], Protocol):
    """Marker port for future multi-operation transactions.

    The first adapter exposes atomic repository operations; this port keeps the
    transaction boundary database-neutral before later stages add recovery.
    """

    def __enter__(self) -> "UnitOfWork": ...
