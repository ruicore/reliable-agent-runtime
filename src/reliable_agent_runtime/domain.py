"""Database-neutral R1 domain contracts for the first execution slice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any

CONTRACT_VERSION = "r1"


class RunState(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    READY = "ready"
    COMPLETED = "completed"
    MODEL_INVALID = "model_invalid"
    TERMINATED = "terminated"
    CANCELLED = "cancelled"


class ActionResultState(StrEnum):
    NOT_STARTED = "not_started"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class DispatchState(StrEnum):
    NOT_DISPATCHED = "not_dispatched"
    INTENT_PERSISTED = "intent_persisted"
    DISPATCHED = "dispatched"


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CancellationState(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    STOP_CONFIRMED = "stop_confirmed"


class ModelValidity(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


@dataclass(frozen=True)
class ToolOutput:
    """Typed tool completion envelope for the R1 adapter."""

    result: ActionResultState
    contract_version: str = CONTRACT_VERSION


class RuntimeError(Exception):
    """Base for errors that are safe to expose at the developer boundary."""


class RequestIdentityConflict(RuntimeError):
    """A request key was reused for different canonical content."""


class ConcurrentSubmission(RuntimeError):
    """Another submitter won the durable request-identity race."""

    def __init__(self, existing: "RunView") -> None:
        super().__init__("request identity was committed concurrently")
        self.existing = existing


class InvalidModelOutput(RuntimeError):
    """The model response did not satisfy the R1 structural contract."""


class ApprovalRequired(RuntimeError):
    """Execution was requested without exact approval."""


class ActionNotFound(RuntimeError):
    """The requested action is not present in durable state."""


class CancellationAccepted(RuntimeError):
    """A cancellation interlock prevents a new dispatch."""


class BudgetExhausted(RuntimeError):
    """A durable retry or execution-time budget prevents a new attempt."""


@dataclass(frozen=True, repr=False)
class ModelInput:
    text: str
    contract_version: str = CONTRACT_VERSION

    def __repr__(self) -> str:
        return f"ModelInput(text_digest={digest_text(self.text)!r}, contract_version={self.contract_version!r})"


@dataclass(frozen=True, repr=False)
class ModelOutput:
    validity: ModelValidity
    title: str = ""
    body: str = ""
    error_code: str | None = None
    contract_version: str = CONTRACT_VERSION

    @property
    def is_valid(self) -> bool:
        return self.validity is ModelValidity.VALID

    def __repr__(self) -> str:
        return (
            "ModelOutput("
            f"validity={self.validity.value!r}, title_digest={digest_text(self.title)!r}, "
            f"body_digest={digest_text(self.body)!r}, error_code={self.error_code!r}, "
            f"contract_version={self.contract_version!r})"
        )


@dataclass(frozen=True, repr=False)
class RunRecord:
    run_id: str
    request_id: str
    input_digest: str
    contract_version: str
    state: RunState

    def __repr__(self) -> str:
        return (
            "RunRecord("
            f"run_id={self.run_id!r}, request_identity_digest={digest_text(self.request_id)!r}, "
            f"input_digest={self.input_digest!r}, contract_version={self.contract_version!r}, "
            f"state={self.state.value!r})"
        )


@dataclass(frozen=True, repr=False)
class ActionRecord:
    action_id: str
    run_id: str
    target: str
    payload: str
    action_digest: str
    approval: ApprovalState
    dispatch: DispatchState
    result: ActionResultState
    cancellation: CancellationState = CancellationState.NOT_REQUESTED

    def __repr__(self) -> str:
        return (
            "ActionRecord("
            f"action_id={self.action_id!r}, run_id={self.run_id!r}, target={self.target!r}, "
            f"payload_digest={digest_text(self.payload)!r}, action_digest={self.action_digest!r}, "
            f"approval={self.approval.value!r}, dispatch={self.dispatch.value!r}, "
            f"result={self.result.value!r}, cancellation={self.cancellation.value!r})"
        )


@dataclass(frozen=True)
class AttemptRecord:
    attempt_id: str
    action_id: str
    dispatch: DispatchState
    result: ActionResultState


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    run_id: str
    kind: str
    sequence: int
    detail_digest: str | None = None


@dataclass(frozen=True)
class BudgetState:
    max_attempts: int | None = None
    attempts_consumed: int = 0
    max_execution_seconds: float | None = None
    execution_seconds_consumed: float = 0.0
    human_wait_seconds: float = 0.0
    execution_started_at: float | None = None


@dataclass(frozen=True)
class RunView:
    run: RunRecord
    action: ActionRecord | None
    attempts: tuple[AttemptRecord, ...]
    events: tuple[EventRecord, ...]
    budget: BudgetState = BudgetState()


def canonicalize_input(value: str) -> str:
    """Canonicalize public text without storing the original in diagnostics."""

    return " ".join(value.split())


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_payload(title: str, body: str) -> str:
    return json.dumps({"body": body, "title": title}, ensure_ascii=True, separators=(",", ":"))


def action_digest(*, target: str, payload: str, contract_version: str = CONTRACT_VERSION) -> str:
    material = json.dumps(
        {"contract_version": contract_version, "payload": payload, "target": target},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return digest_text(material)


def safe_model_output(output: Any) -> ModelOutput:
    """Validate a model adapter response at the application boundary."""

    if not isinstance(output, ModelOutput):
        raise InvalidModelOutput("model output is not the R1 structured type")
    if output.contract_version != CONTRACT_VERSION:
        raise InvalidModelOutput("model output contract version is unsupported")
    if output.is_valid and (not output.title.strip() or not output.body.strip()):
        raise InvalidModelOutput("valid model output requires title and body")
    if output.validity is ModelValidity.INVALID and not output.error_code:
        raise InvalidModelOutput("invalid model output requires an error code")
    return output
