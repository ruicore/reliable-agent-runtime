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


@dataclass(frozen=True)
class ModelInput:
    text: str
    contract_version: str = CONTRACT_VERSION


@dataclass(frozen=True)
class ModelOutput:
    validity: ModelValidity
    title: str = ""
    body: str = ""
    error_code: str | None = None
    contract_version: str = CONTRACT_VERSION

    @property
    def is_valid(self) -> bool:
        return self.validity is ModelValidity.VALID


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    request_id: str
    input_digest: str
    contract_version: str
    state: RunState


@dataclass(frozen=True)
class ActionRecord:
    action_id: str
    run_id: str
    target: str
    payload: str
    action_digest: str
    approval: ApprovalState
    dispatch: DispatchState
    result: ActionResultState


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


@dataclass(frozen=True)
class RunView:
    run: RunRecord
    action: ActionRecord | None
    attempts: tuple[AttemptRecord, ...]
    events: tuple[EventRecord, ...]


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
