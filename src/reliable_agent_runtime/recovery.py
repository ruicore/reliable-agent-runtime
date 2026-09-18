"""Database-neutral recovery decisions for the first Stage 02 increment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .domain import ActionResultState, CONTRACT_VERSION, RuntimeError


class RecoveryDecisionKind(StrEnum):
    NO_ACTION = "no_action"
    QUERY = "query"
    RETRY = "retry"
    HUMAN_ATTENTION = "human_attention"


class UnsupportedAdapterGuarantee(RuntimeError):
    """The adapter guarantee declaration cannot be used by this contract."""


@dataclass(frozen=True)
class AdapterGuarantees:
    """Verified facts supplied by a tool adapter, not inferred by Runtime."""

    queryable: bool = False
    deduplication_verified: bool = False
    deduplication_scope: str | None = None
    retry_safe: bool = False
    guarantee_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.guarantee_version != CONTRACT_VERSION:
            raise UnsupportedAdapterGuarantee("adapter guarantee version is unsupported")
        if self.deduplication_verified and not self.deduplication_scope:
            raise ValueError("verified deduplication requires an explicit scope")
        if self.retry_safe and not self.deduplication_verified:
            raise ValueError("retry safety requires verified deduplication")


@dataclass(frozen=True)
class RecoveryDecision:
    kind: RecoveryDecisionKind
    reason: str
    guarantee_version: str = CONTRACT_VERSION


@dataclass(frozen=True)
class RecoveryMaterial:
    """Minimal historical identity needed to consider safe recovery."""

    contract_version: str
    input_digest: str

    def require_compatible(self, *, contract_version: str, input_digest: str) -> None:
        if self.contract_version != contract_version:
            raise IncompatibleRecoveryMaterial("recovery material contract version is incompatible")
        if self.input_digest != input_digest:
            raise IncompatibleRecoveryMaterial("recovery material input identity is incompatible")


class IncompatibleRecoveryMaterial(RuntimeError):
    """Historical recovery material cannot safely be used for this run."""


class RecoveryPolicy:
    """Conservative decision function; it never mutates durable state."""

    @staticmethod
    def decide(
        *,
        result: ActionResultState,
        attempt_count: int,
        max_attempts: int | None,
        guarantees: AdapterGuarantees,
    ) -> RecoveryDecision:
        if attempt_count < 0:
            raise ValueError("attempt count cannot be negative")
        if result is not ActionResultState.UNKNOWN:
            return RecoveryDecision(RecoveryDecisionKind.NO_ACTION, "action result is not unknown")
        if guarantees.queryable:
            return RecoveryDecision(RecoveryDecisionKind.QUERY, "adapter declares a queryable result")
        if guarantees.retry_safe and max_attempts is not None and attempt_count < max_attempts:
            return RecoveryDecision(RecoveryDecisionKind.RETRY, "verified retry safety and remaining attempts")
        if guarantees.retry_safe and max_attempts is None:
            return RecoveryDecision(RecoveryDecisionKind.HUMAN_ATTENTION, "retry limit is not declared")
        return RecoveryDecision(
            RecoveryDecisionKind.HUMAN_ATTENTION,
            "unknown result has no verified query or retry guarantee",
        )
