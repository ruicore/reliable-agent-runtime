from __future__ import annotations

import json
import re

from reliable_agent_runtime import DeterministicModel, IndependentObserver, RuntimeService, SQLiteRepository, SideEffectStore
from reliable_agent_runtime.domain import ActionResultState, ToolOutput
from reliable_agent_runtime.evidence import REPORT_VERSION, redact_text
from reliable_agent_runtime.tool import SimulatedTool


def make_service(tool=None):
    effects = SideEffectStore()
    service = RuntimeService(SQLiteRepository(), DeterministicModel(), tool or SimulatedTool(effects))
    return service, effects


def test_report_is_versioned_minimized_and_json_serializable() -> None:
    canary = "RAR_CANARY_STAGE04_PRIVATE"
    service, effects = make_service()
    view = service.submit(request_id="stage04-report", text=canary)
    assert view.action is not None
    service.approve(view.action.action_id)
    completed = service.execute(run_id=view.run.run_id)
    report = service.report(
        completed.run.run_id,
        scenario="normal_approved_execution",
        expected="confirmed completion",
        independent_observation="observer:1",
    )

    encoded = json.dumps(report, sort_keys=True)
    assert REPORT_VERSION == report["report_version"]
    assert canary not in encoded
    assert canary not in repr(completed)
    assert report["observed"]["run_state"] == "completed"
    assert report["evidence"]["independent_observation"] == "attached"
    assert report["reproducibility"]["decision_signature"]
    assert effects.count() == 1


def test_redaction_helper_covers_explicit_canaries_and_credential_shapes() -> None:
    canary = "RAR_CANARY_EXPLICIT"
    sentence = f"input={canary} bearer secret-value ghp-1234567890abcdef"
    safe = redact_text(sentence, canaries=[canary])
    assert canary not in safe
    assert "secret-value" not in safe
    assert "ghp-1234567890abcdef" not in safe
    assert safe.count("[REDACTED]") == 3


def test_repeated_fault_reports_have_same_decision_signature() -> None:
    class UnknownTool:
        def execute(self, *, action_id: str, target: str, payload: str) -> object:
            return {"ack": "received"}

    signatures = []
    for request_id in ("fault-run-1", "fault-run-2"):
        service, _ = make_service(UnknownTool())
        view = service.submit(request_id=request_id, text="repeated unknown fault")
        assert view.action is not None
        service.approve(view.action.action_id)
        result = service.execute(run_id=view.run.run_id)
        report = service.report(result.run.run_id, scenario="unknown_tool_response", fault_point="tool_result")
        signatures.append(report["reproducibility"]["decision_signature"])
        assert report["observed"]["action_result"] == ActionResultState.UNKNOWN.value
        assert "simulator evidence" in " ".join(report["unverified"])

    assert signatures[0] == signatures[1]


def test_independent_observer_remains_separate_from_runtime_report() -> None:
    effects = SideEffectStore()
    observer = IndependentObserver(effects)
    service = RuntimeService(SQLiteRepository(), DeterministicModel(), SimulatedTool(effects))
    view = service.submit(request_id="observer-separation", text="observer separation")
    assert view.action is not None
    service.approve(view.action.action_id)
    result = service.execute(run_id=view.run.run_id)
    report = service.report(result.run.run_id)
    assert observer.find(result.action.action_id) is not None
    assert report["evidence"]["independent_observation"] == "not_attached"
    assert "payload" not in json.dumps(report).lower()


def test_human_report_is_compact_and_does_not_contain_raw_action_content() -> None:
    service, _ = make_service()
    view = service.submit(request_id="human-summary", text="human summary canary")
    assert view.action is not None
    service.approve(view.action.action_id)
    service.execute(run_id=view.run.run_id)
    summary = service.human_report(view.run.run_id)
    assert len(summary) < 512
    assert "human summary canary" not in summary
    assert re.search(r"decision_signature=[0-9a-f]{64}", summary)
