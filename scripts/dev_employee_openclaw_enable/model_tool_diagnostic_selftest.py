from __future__ import annotations

from .model_tool_diagnostic_result import (
    CAPABILITY_RESULT,
    PASS_RESULT,
    ROUTING_RESULT,
    classify_model_tool_diagnostic,
    sanitize_agent_acceptance,
)
from .models import CheckRecorder, RunState


CONTROL = "session_status"
ORIS = "oris_queue_status"


def _automatic(seen: list[str]) -> dict:
    return {
        "accepted": set(seen) == {CONTROL, ORIS},
        "agent_targeted_explicitly": True,
        "gateway_transport_proven": True,
        "persisted_native_session": True,
        "same_cli_session_requested": True,
        "turns": [
            {
                "intent": "control",
                "expected_tool": CONTROL,
                "returncode": 0,
                "duration_ms": 10.0,
                "output_present": True,
                "structured_output_valid": True,
                "gateway_transport_ok": True,
                "reported_tool_names": [CONTROL, "unrelated_tool"],
                "stdout_bytes": 10,
                "stderr_bytes": 0,
            }
        ],
        "telemetry": {
            "accepted": set(seen) == {CONTROL, ORIS},
            "expected_tools_seen": seen,
            "unexpected_tools_seen": ["unrelated_tool"],
            "event_counts": {"agent_end": 2, "model_call_ended": 2},
            "all_event_counts": {"after_tool_call": len(seen)},
            "providers_seen": ["runtime-provider"],
            "models_seen": ["runtime-model"],
            "persisted_session": True,
            "correlation_mode": "session_hash",
            "schema_ok": True,
            "content_safe": True,
            "parent_permissions_ok": True,
            "file_permissions_ok": True,
            "only_approved_tools_used": True,
            "records_after_start": 6,
            "correlated_records": 6,
            "session_records": 6,
            "metrics": {
                "model_duration": {"available": True, "count": 2},
                "total_agent_duration": {"available": True, "count": 2},
                "tool_duration": {
                    CONTROL: {"available": True, "count": 1},
                    ORIS: {"available": True, "count": 1},
                    "unrelated_tool": {"available": True, "count": 1},
                },
            },
        },
    }


def _classified(seen: list[str]) -> RunState:
    state = RunState()
    classify_model_tool_diagnostic(
        state,
        CheckRecorder(),
        _automatic(seen),
        CONTROL,
        ORIS,
    )
    return state


def test_model_tool_diagnostic_result() -> None:
    sanitized = sanitize_agent_acceptance(
        _automatic([CONTROL, ORIS]),
        {CONTROL, ORIS},
    )
    assert sanitized["turns"][0]["reported_tool_names"] == [CONTROL]
    assert sanitized["telemetry"]["expected_tools_seen"] == sorted([CONTROL, ORIS])
    assert set(sanitized["telemetry"]["metrics"]["tool_duration"]) == {
        CONTROL,
        ORIS,
    }
    assert sanitized["telemetry"]["unexpected_tool_count"] == 1
    assert sanitized["unrelated_tool_names_recorded"] is False
    assert _classified([CONTROL, ORIS]).result == PASS_RESULT
    assert _classified([CONTROL]).result == ROUTING_RESULT
    assert _classified([]).result == CAPABILITY_RESULT
