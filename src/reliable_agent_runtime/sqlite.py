"""SQLite/SQLAlchemy infrastructure adapter for the database-neutral ports."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Sequence
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from .domain import (
    ActionNotFound,
    ActionRecord,
    ActionResultState,
    ApprovalState,
    AttemptRecord,
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
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def _enable_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
            row.approval = ApprovalState.APPROVED.value
            row.run.state = RunState.READY.value

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
            action.dispatch = DispatchState.DISPATCHED.value
            attempt.dispatch = DispatchState.DISPATCHED.value
            session.add(self._event_row(event))

    def record_result(self, action_id: str, attempt_id: str, result: str, event: EventRecord) -> None:
        with self._write_lock, self._sessions.begin() as session:
            action = session.get(ActionRow, action_id)
            attempt = session.get(AttemptRow, attempt_id)
            if not action or not attempt:
                raise ActionNotFound(f"action {action_id} was not found")
            action.result = result
            attempt.result = result
            if result == ActionResultState.SUCCEEDED.value:
                action.run.state = RunState.COMPLETED.value
            session.add(self._event_row(event))

    @staticmethod
    def _event_row(event_record: EventRecord) -> EventRow:
        return EventRow(
            event_id=event_record.event_id,
            run_id=event_record.run_id,
            kind=event_record.kind,
            sequence=event_record.sequence,
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
            )
            if action
            else None
        )
        attempts = tuple(
            AttemptRecord(a.attempt_id, a.action_id, DispatchState(a.dispatch), ActionResultState(a.result))
            for a in (action.attempts if action else [])
        )
        events = tuple(EventRecord(e.event_id, e.run_id, e.kind, e.sequence) for e in sorted(row.events, key=lambda e: e.sequence))
        return RunView(
            run=RunRecord(row.run_id, row.request_id, row.input_digest, row.contract_version, RunState(row.state)),
            action=action_record,
            attempts=attempts,
            events=events,
        )


def new_id() -> str:
    return uuid4().hex
