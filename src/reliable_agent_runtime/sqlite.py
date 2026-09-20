"""SQLite/SQLAlchemy infrastructure adapter for the database-neutral ports."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
import time
from typing import Sequence
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from .domain import (
    ActionNotFound,
    ActionRecord,
    ActionResultState,
    ApprovalState,
    ApprovalRequired,
    AttemptRecord,
    BudgetExhausted,
    BudgetState,
    CancellationAccepted,
    CancellationState,
    DispatchState,
    EventRecord,
    ConcurrentSubmission,
    RunRecord,
    RunState,
    RunView,
)


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_execution_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_seconds_consumed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    human_wait_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    execution_started_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actions: Mapped[list["ActionRow"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    events: Mapped[list["EventRow"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ActionRow(Base):
    __tablename__ = "actions"
    action_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, unique=True)
    target: Mapped[str] = mapped_column(String(256), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    action_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    approval: Mapped[str] = mapped_column(String(32), nullable=False)
    dispatch: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    cancellation: Mapped[str] = mapped_column(String(32), nullable=False, default=CancellationState.NOT_REQUESTED.value)
    approved_action_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_input_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run: Mapped[RunRow] = relationship(back_populates="actions")
    attempts: Mapped[list["AttemptRow"]] = relationship(back_populates="action", cascade="all, delete-orphan")


class AttemptRow(Base):
    __tablename__ = "attempts"
    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action_id: Mapped[str] = mapped_column(ForeignKey("actions.action_id"), nullable=False)
    dispatch: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[ActionRow] = relationship(back_populates="attempts")


class EventRow(Base):
    __tablename__ = "events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    detail_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run: Mapped[RunRow] = relationship(back_populates="events")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SQLiteRepository:
    """SQLAlchemy implementation; only this module imports SQLAlchemy."""

    def __init__(self, url: str = "sqlite:///:memory:") -> None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        kwargs = {"connect_args": connect_args}
        if url == "sqlite:///:memory:":
            kwargs["poolclass"] = StaticPool
        self.engine: Engine = create_engine(url, **kwargs)
        self._write_lock = Lock()
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._enable_foreign_keys)
        Base.metadata.create_all(self.engine)
        self._migrate_sqlite_schema()
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def _enable_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def _migrate_sqlite_schema(self) -> None:
        """Apply the small additive migration needed by the Stage 02 event contract."""

        if self.engine.dialect.name != "sqlite":
            return
        with self.engine.begin() as connection:
            event_columns = {
                row[1]
                for row in connection.exec_driver_sql("PRAGMA table_info(events)").fetchall()
            }
            if "detail_digest" not in event_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE events ADD COLUMN detail_digest VARCHAR(64)"
                )
            run_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(runs)").fetchall()}
            run_migrations = {
                "max_attempts": "ALTER TABLE runs ADD COLUMN max_attempts INTEGER",
                "max_execution_seconds": "ALTER TABLE runs ADD COLUMN max_execution_seconds FLOAT",
                "execution_seconds_consumed": "ALTER TABLE runs ADD COLUMN execution_seconds_consumed FLOAT NOT NULL DEFAULT 0.0",
                "human_wait_seconds": "ALTER TABLE runs ADD COLUMN human_wait_seconds FLOAT NOT NULL DEFAULT 0.0",
                "execution_started_at": "ALTER TABLE runs ADD COLUMN execution_started_at FLOAT",
            }
            for name, statement in run_migrations.items():
                if name not in run_columns:
                    connection.exec_driver_sql(statement)
            action_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(actions)").fetchall()}
            action_migrations = {
                "cancellation": "ALTER TABLE actions ADD COLUMN cancellation VARCHAR(32) NOT NULL DEFAULT 'not_requested'",
                "approved_action_digest": "ALTER TABLE actions ADD COLUMN approved_action_digest VARCHAR(64)",
                "approved_input_digest": "ALTER TABLE actions ADD COLUMN approved_input_digest VARCHAR(64)",
            }
            for name, statement in action_migrations.items():
                if name not in action_columns:
                    connection.exec_driver_sql(statement)

    def find_by_request(self, request_id: str) -> RunView | None:
        with self._write_lock, self._sessions() as session:
            row = session.scalar(select(RunRow).where(RunRow.request_id == request_id))
            return self._view(session, row) if row else None

    def persist_submission(self, run: RunRecord, action: ActionRecord | None, events: Sequence[EventRecord]) -> None:
        try:
            with self._write_lock, self._sessions.begin() as session:
                row = RunRow(
                    run_id=run.run_id,
                    request_id=run.request_id,
                    input_digest=run.input_digest,
                    contract_version=run.contract_version,
                    state=run.state.value,
                    created_at=_utcnow(),
                )
                session.add(row)
                if action:
                    session.add(
                        ActionRow(
                            action_id=action.action_id,
                            run_id=action.run_id,
                            target=action.target,
                            payload=action.payload,
                            action_digest=action.action_digest,
                            approval=action.approval.value,
                            dispatch=action.dispatch.value,
                            result=action.result.value,
                        )
                    )
                for event_record in events:
                    session.add(self._event_row(event_record))
        except IntegrityError:
            existing = self.find_by_request(run.request_id)
            if existing is not None:
                raise ConcurrentSubmission(existing) from None
            raise

    def get_view(self, run_id: str) -> RunView:
        with self._write_lock, self._sessions() as session:
            row = session.get(RunRow, run_id)
            if not row:
                raise ActionNotFound(f"run {run_id} was not found")
            return self._view(session, row)

    def approve(self, action_id: str) -> None:
        with self._write_lock, self._sessions.begin() as session:
            row = session.get(ActionRow, action_id)
            if not row:
                raise ActionNotFound(f"action {action_id} was not found")
            if row.run.state == RunState.CANCELLED.value:
                raise CancellationAccepted("cancelled run cannot be approved")
            row.approval = ApprovalState.APPROVED.value
            row.approved_action_digest = row.action_digest
            row.approved_input_digest = row.run.input_digest
            row.run.state = RunState.READY.value

    def invalidate_approval(self, action_id: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            action = session.get(ActionRow, action_id)
            if not action:
                raise ActionNotFound(f"action {action_id} was not found")
            action.approval = ApprovalState.REJECTED.value
            action.approved_action_digest = None
            action.approved_input_digest = None
            session.add(self._event_row(event))

    def configure_budgets(
        self,
        run_id: str,
        max_attempts: int | None,
        max_execution_seconds: float | None,
    ) -> None:
        if max_attempts is not None and max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if max_execution_seconds is not None and max_execution_seconds <= 0:
            raise ValueError("max_execution_seconds must be positive")
        with self._write_lock, self._sessions.begin() as session:
            run = session.get(RunRow, run_id)
            if not run:
                raise ActionNotFound(f"run {run_id} was not found")
            run.max_attempts = max_attempts
            run.max_execution_seconds = max_execution_seconds

    def budget_state(self, run_id: str) -> BudgetState:
        with self._write_lock, self._sessions() as session:
            run = session.get(RunRow, run_id)
            if not run:
                raise ActionNotFound(f"run {run_id} was not found")
            attempts = session.scalar(
                select(func.count(AttemptRow.attempt_id)).join(ActionRow).where(ActionRow.run_id == run_id)
            ) or 0
            active_seconds = 0.0
            if run.execution_started_at is not None:
                active_seconds = max(0.0, time.time() - run.execution_started_at)
            return BudgetState(
                max_attempts=run.max_attempts,
                attempts_consumed=int(attempts),
                max_execution_seconds=run.max_execution_seconds,
                execution_seconds_consumed=float(run.execution_seconds_consumed or 0.0) + active_seconds,
                human_wait_seconds=float(run.human_wait_seconds or 0.0),
                execution_started_at=run.execution_started_at,
            )

    def record_human_wait(self, run_id: str, seconds: float, event: EventRecord) -> None:
        if seconds < 0:
            raise ValueError("human wait cannot be negative")
        with self._write_lock, self._sessions.begin() as session:
            run = session.get(RunRow, run_id)
            if not run:
                raise ActionNotFound(f"run {run_id} was not found")
            run.human_wait_seconds = float(run.human_wait_seconds or 0.0) + seconds
            session.add(self._event_row(event))

    def prepare_attempt(self, attempt: AttemptRecord, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            action = session.get(ActionRow, attempt.action_id)
            if not action:
                raise ActionNotFound(f"action {attempt.action_id} was not found")
            run = action.run
            if action.cancellation in (
                CancellationState.ACCEPTED.value,
                CancellationState.STOP_CONFIRMED.value,
            ):
                raise CancellationAccepted("cancellation prevents a new attempt")
            if (
                action.approval != ApprovalState.APPROVED.value
                or action.approved_action_digest != action.action_digest
                or action.approved_input_digest != run.input_digest
            ):
                raise ApprovalRequired("approval is missing or no longer matches the action")
            consumed = session.scalar(
                select(func.count(AttemptRow.attempt_id)).where(AttemptRow.action_id == action.action_id)
            ) or 0
            if run.max_attempts is not None and consumed >= run.max_attempts:
                raise BudgetExhausted("retry-count budget is exhausted")
            elapsed = float(run.execution_seconds_consumed or 0.0)
            if run.execution_started_at is not None:
                elapsed += max(0.0, time.time() - run.execution_started_at)
                if run.max_execution_seconds is not None and elapsed >= run.max_execution_seconds:
                    raise BudgetExhausted("execution-time budget is exhausted")
                raise BudgetExhausted("an in-flight attempt prevents a new dispatch")
            if run.max_execution_seconds is not None and elapsed >= run.max_execution_seconds:
                raise BudgetExhausted("execution-time budget is exhausted")
            if run.execution_started_at is None:
                run.execution_started_at = time.time()
            session.add(
                AttemptRow(
                    attempt_id=attempt.attempt_id,
                    action_id=attempt.action_id,
                    dispatch=attempt.dispatch.value,
                    result=attempt.result.value,
                    created_at=_utcnow(),
                )
            )
            session.add(self._event_row(event))

    def request_cancel(self, run_id: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            run = session.get(RunRow, run_id)
            if not run or not run.actions:
                raise ActionNotFound(f"run {run_id} was not found")
            action = run.actions[0]
            if action.cancellation == CancellationState.NOT_REQUESTED.value:
                action.cancellation = CancellationState.REQUESTED.value
            session.add(self._event_row(event))

    def accept_cancel(self, run_id: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            run = session.get(RunRow, run_id)
            if not run or not run.actions:
                raise ActionNotFound(f"run {run_id} was not found")
            action = run.actions[0]
            if action.cancellation == CancellationState.STOP_CONFIRMED.value:
                session.add(self._event_row(event))
                return
            if action.cancellation not in (
                CancellationState.REQUESTED.value,
                CancellationState.ACCEPTED.value,
            ):
                raise CancellationAccepted("cancellation must be requested before acceptance")
            action.cancellation = CancellationState.ACCEPTED.value
            run.state = RunState.CANCELLED.value
            session.add(self._event_row(event))

    def confirm_stopped(self, run_id: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            run = session.get(RunRow, run_id)
            if not run or not run.actions:
                raise ActionNotFound(f"run {run_id} was not found")
            action = run.actions[0]
            if action.cancellation not in (
                CancellationState.ACCEPTED.value,
                CancellationState.STOP_CONFIRMED.value,
            ):
                raise CancellationAccepted("cancellation must be accepted before stop confirmation")
            action.cancellation = CancellationState.STOP_CONFIRMED.value
            session.add(self._event_row(event))

    def create_attempt(self, attempt: AttemptRecord, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            action = session.get(ActionRow, attempt.action_id)
            if not action:
                raise ActionNotFound(f"action {attempt.action_id} was not found")
            session.add(
                AttemptRow(
                    attempt_id=attempt.attempt_id,
                    action_id=attempt.action_id,
                    dispatch=attempt.dispatch.value,
                    result=attempt.result.value,
                    created_at=_utcnow(),
                )
            )
            session.add(self._event_row(event))

    def mark_dispatched(self, action_id: str, attempt_id: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            action = session.get(ActionRow, action_id)
            attempt = session.get(AttemptRow, attempt_id)
            if not action or not attempt:
                raise ActionNotFound(f"action {action_id} was not found")
            if action.cancellation in (
                CancellationState.ACCEPTED.value,
                CancellationState.STOP_CONFIRMED.value,
            ):
                raise CancellationAccepted("cancellation accepted before dispatch")
            action.dispatch = DispatchState.DISPATCHED.value
            attempt.dispatch = DispatchState.DISPATCHED.value
            session.add(self._event_row(event))

    def suppress_attempt(self, action_id: str, attempt_id: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            action = session.get(ActionRow, action_id)
            attempt = session.get(AttemptRow, attempt_id)
            if not action or not attempt:
                raise ActionNotFound(f"action {action_id} was not found")
            attempt.result = ActionResultState.REJECTED.value
            if action.run.execution_started_at is not None:
                action.run.execution_seconds_consumed = float(action.run.execution_seconds_consumed or 0.0) + max(
                    0.0,
                    time.time() - action.run.execution_started_at,
                )
                action.run.execution_started_at = None
            session.add(self._event_row(event))

    def record_result(self, action_id: str, attempt_id: str, result: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            action = session.get(ActionRow, action_id)
            attempt = session.get(AttemptRow, attempt_id)
            if not action or not attempt:
                raise ActionNotFound(f"action {action_id} was not found")
            action.result = result
            attempt.result = result
            if action.run.execution_started_at is not None:
                action.run.execution_seconds_consumed = float(action.run.execution_seconds_consumed or 0.0) + max(
                    0.0,
                    time.time() - action.run.execution_started_at,
                )
                action.run.execution_started_at = None
            if result == ActionResultState.SUCCEEDED.value and action.run.state != RunState.TERMINATED.value:
                if action.run.state != RunState.CANCELLED.value:
                    action.run.state = RunState.COMPLETED.value
            session.add(self._event_row(event))

    def append_event(self, event: EventRecord, state: RunState | None = None) -> None:
        with self._write_lock, self._sessions.begin() as session:
            run = session.get(RunRow, event.run_id)
            if not run:
                raise ActionNotFound(f"run {event.run_id} was not found")
            if state is not None:
                run.state = state.value
            session.add(self._event_row(event))

    @staticmethod
    def _event_row(event_record: EventRecord) -> EventRow:
        return EventRow(
            event_id=event_record.event_id,
            run_id=event_record.run_id,
            kind=event_record.kind,
            sequence=event_record.sequence,
            detail_digest=event_record.detail_digest,
            created_at=_utcnow(),
        )

    @staticmethod
    def _view(session: Session, row: RunRow) -> RunView:
        action = row.actions[0] if row.actions else None
        action_record = (
            ActionRecord(
                action_id=action.action_id,
                run_id=action.run_id,
                target=action.target,
                payload=action.payload,
                action_digest=action.action_digest,
                approval=ApprovalState(action.approval),
                dispatch=DispatchState(action.dispatch),
                result=ActionResultState(action.result),
                cancellation=CancellationState(action.cancellation),
            )
            if action
            else None
        )
        attempts = tuple(
            AttemptRecord(a.attempt_id, a.action_id, DispatchState(a.dispatch), ActionResultState(a.result))
            for a in (action.attempts if action else [])
        )
        events = tuple(
            EventRecord(e.event_id, e.run_id, e.kind, e.sequence, e.detail_digest)
            for e in sorted(row.events, key=lambda e: e.sequence)
        )
        return RunView(
            run=RunRecord(row.run_id, row.request_id, row.input_digest, row.contract_version, RunState(row.state)),
            action=action_record,
            attempts=attempts,
            events=events,
            budget=BudgetState(
                max_attempts=row.max_attempts,
                attempts_consumed=len(attempts),
                max_execution_seconds=row.max_execution_seconds,
                execution_seconds_consumed=float(row.execution_seconds_consumed or 0.0)
                + (max(0.0, time.time() - row.execution_started_at) if row.execution_started_at else 0.0),
                human_wait_seconds=float(row.human_wait_seconds or 0.0),
                execution_started_at=row.execution_started_at,
            ),
        )


def new_id() -> str:
    return uuid4().hex
