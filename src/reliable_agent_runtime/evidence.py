"""Versioned, minimized evidence helpers for the Phase 1 delivery contract."""

from __future__ import annotations

import json
import platform
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Iterable

from .domain import CONTRACT_VERSION, digest_text

REPORT_VERSION = "r1-report-1"
REDACTION_MARKER = "[REDACTED]"

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~-]+"),
    re.compile(r"\b(?:sk|ghp|xoxb|xoxp)-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bSYNTHETIC_CANARY_[A-Za-z0-9_-]+\b"),
)
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_.: -]{1,128}$")


def redact_text(value: str, *, canaries: Iterable[str] = ()) -> str:
    """Remove explicit canaries and common credential-shaped values.

    Reports normally exclude raw text altogether. This helper is for callers
    that need a safe diagnostic sentence while preserving a stable shape.
    """

    redacted = value
    for canary in sorted((item for item in canaries if item), key=len, reverse=True):
        redacted = redacted.replace(canary, REDACTION_MARKER)
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(REDACTION_MARKER, redacted)
    return redacted


def package_version() -> str:
    try:
        return version("reliable-agent-runtime")
    except PackageNotFoundError:
        return "source-checkout"


def safe_label(value: str | None, *, default: str = "unspecified") -> str:
    """Keep report labels bounded and reject arbitrary raw diagnostic text."""

    if value is None:
        return default
    cleaned = redact_text(value)
    if cleaned != value:
        return "redacted_label"
    if _SAFE_LABEL.fullmatch(value):
        return value
    return f"label_digest:{digest_text(value)}"


def environment_fingerprint() -> dict[str, str]:
    """Return reproducible environment identity without local paths or secrets."""

    return {
        "python": platform.python_version(),
        "implementation": sys.implementation.name,
        "platform": platform.system().lower(),
        "package": package_version(),
    }


def decision_signature(*, run_state: str, action_result: str | None, cancellation: str | None, events: Iterable[str]) -> str:
    """Hash observable decisions so repeated faults can be compared safely."""

    material = json.dumps(
        {
            "action_result": action_result,
            "cancellation": cancellation,
            "events": list(events),
            "run_state": run_state,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return digest_text(material)


def concise_human_summary(report: dict[str, Any]) -> str:
    """Render a short, raw-data-free explanation from a machine report."""

    observed = report["observed"]
    return (
        f"scenario={report['scenario']['name']}; "
        f"run_state={observed['run_state']}; "
        f"action_result={observed['action_result']}; "
        f"attempts={observed['attempt_count']}; "
        f"decision_signature={report['reproducibility']['decision_signature']}"
    )
