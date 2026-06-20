from __future__ import annotations

from typing import Any

from .models import CheckRecorder, RunState


PASS_RESULT = "MODEL_TOOL_CALL_AND_ORIS_ROUTING_PASS"
CAPABILITY_RESULT = "MODEL_TOOL_CALL_CAPABILITY_NOT_DEMONSTRATED"
ROUTING_RESULT = "ORIS_AGENT_HARNESS_ROUTING_FAILED"
INCONSISTENT_RESULT = "MODEL_TOOL_DIAGNOSTIC_INCONSISTENT"


def _filtered_names(value: Any, allowed: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(
        {
            item
            for item in value
            if isinstance(item, str) and item in allowed
        }
    )


def sanitize_agent_acceptance(
    automatic: dict[str, Any],
    expected_tools: set[str],
) -> dict[str, Any]:
    telemetry = automatic.get("telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    turns: list[dict[str, Any]] = []
    raw_turns = automatic.get("turns")
    if isinstance(raw_turns, list):
        for item in raw_turns:
            if not isinstance(item, dict):
                continue
            expected = item.get("expected_tool")
            reported = _filtered_names(item.get("reported_tool_names"), expected_tools)
            turns.append(
                {
                    "intent": item.get("intent") if isinstance(item.get("intent"), str) else "",
                    "expected_tool": expected if expected in expected_tools else "",
                    "returncode": item.get("returncode"),
                    "duration_ms": item.get("duration_ms"),
                    "output_present": item.get("output_present") is True,
                    "structured_output_valid": item.get("structured_output_valid") is True,
                    "gateway_transport_ok": item.get("gateway_transport_ok") is True,
                    "reported_tool_names": reported,
                    "stdout_bytes": item.get("stdout_bytes"),
                    "stderr_bytes": item.get("stderr_bytes"),
                }
            )
    metrics = telemetry.get("metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    tool_metrics = metrics.get("tool_duration")
    tool_metrics = tool_metrics if isinstance(tool_metrics, dict) else {}
    return {
        "accepted": automatic.get("accepted") is True,
        "reason": automatic.get("reason") if isinstance(automatic.get("reason"), str) else None,
        "agent_targeted_explicitly": automatic.get("agent_targeted_explicitly") is True,
        "gateway_transport_proven": automatic.get("gateway_transport_proven") is True,
        "persisted_native_session": automatic.get("persisted_native_session") is True,
        "same_cli_session_requested": automatic.get("same_cli_session_requested") is True,
        "turns": turns,
        "telemetry": {
            "accepted": telemetry.get("accepted") is True,
            "expected_tools_seen": _filtered_names(
                telemetry.get("expected_tools_seen"),
                expected_tools,
            ),
            "unexpected_tool_count": len(
                telemetry.get("unexpected_tools_seen", [])
                if isinstance(telemetry.get("unexpected_tools_seen"), list)
                else []
            ),
            "event_counts": telemetry.get("event_counts")
            if isinstance(telemetry.get("event_counts"), dict)
            else {},
            "all_event_counts": telemetry.get("all_event_counts")
            if isinstance(telemetry.get("all_event_counts"), dict)
            else {},
            "providers_seen": telemetry.get("providers_seen")
            if isinstance(telemetry.get("providers_seen"), list)
            else [],
            "models_seen": telemetry.get("models_seen")
            if isinstance(telemetry.get("models_seen"), list)
            else [],
            "persisted_session": telemetry.get("persisted_session") is True,
            "correlation_mode": telemetry.get("correlation_mode")
            if isinstance(telemetry.get("correlation_mode"), str)
            else "",
            "schema_ok": telemetry.get("schema_ok") is True,
            "content_safe": telemetry.get("content_safe") is True,
            "parent_permissions_ok": telemetry.get("parent_permissions_ok") is True,
            "file_permissions_ok": telemetry.get("file_permissions_ok") is True,
            "only_authorized_tools_used": telemetry.get("only_authorized_tools_used")
            is True,
            "records_after_start": telemetry.get("records_after_start"),
            "correlated_records": telemetry.get("correlated_records"),
            "session_records": telemetry.get("session_records"),
            "metrics": {
                "model_duration": metrics.get("model_duration", {}),
                "total_agent_duration": metrics.get("total_agent_duration", {}),
                "tool_duration": {
                    name: tool_metrics.get(name, {})
                    for name in sorted(expected_tools)
                },
            },
        },
        "conversation_content_recorded": False,
        "tool_arguments_or_results_recorded": False,
        "session_identifier_recorded": False,
        "unrelated_tool_names_recorded": False,
    }


def classify_model_tool_diagnostic(
    state: RunState,
    checks: CheckRecorder,
    automatic: dict[str, Any],
    control_tool: str,
    oris_tool: str,
) -> None:
    expected = {control_tool, oris_tool}
    sanitized = sanitize_agent_acceptance(automatic, expected)
    telemetry = sanitized["telemetry"]
    seen = set(telemetry["expected_tools_seen"])
    control_called = control_tool in seen
    oris_called = oris_tool in seen
    privacy_ok = bool(
        telemetry["schema_ok"]
        and telemetry["content_safe"]
        and telemetry["parent_permissions_ok"]
        and telemetry["file_permissions_ok"]
        and telemetry["only_authorized_tools_used"]
    )
    state.telemetry_privacy_pass = privacy_ok
    state.native_agent_acceptance_pass = control_called and oris_called
    state.details["native_agent_acceptance"] = sanitized
    state.details["model_tool_diagnostic"] = {
        "control_tool_called": control_called,
        "oris_tool_called": oris_called,
        "provider_runtime_facts": telemetry["providers_seen"],
        "model_runtime_facts": telemetry["models_seen"],
        "persisted_session": telemetry["persisted_session"],
        "gateway_transport_proven": sanitized["gateway_transport_proven"],
        "telemetry_privacy_pass": privacy_ok,
        "conversation_content_recorded": False,
        "tool_arguments_or_results_recorded": False,
        "session_identifier_recorded": False,
        "unrelated_tool_names_recorded": False,
    }
    if not privacy_ok:
        state.result = "MODEL_TOOL_DIAGNOSTIC_PRIVACY_FAILED"
        state.failure_code = "telemetry_privacy_failed"
        state.next_action = "FIX_TELEMETRY_PRIVACY_BEFORE_RETRY"
        checks.fail_check("model_tool_diagnostic_privacy", state.failure_code)
    elif control_called and oris_called:
        state.result = PASS_RESULT
        state.failure_code = ""
        state.next_action = "RUN_THREE_TOOL_NATIVE_LANGUAGE_ACCEPTANCE"
        checks.pass_check("model_tool_call_capability", "safe built-in tool called")
        checks.pass_check("oris_agent_harness_routing", "ORIS queue tool called")
    elif control_called:
        state.result = ROUTING_RESULT
        state.failure_code = "oris_tool_not_called"
        state.next_action = "FIX_ORIS_AGENT_HARNESS_ROUTING"
        checks.pass_check("model_tool_call_capability", "safe built-in tool called")
        checks.fail_check("oris_agent_harness_routing", state.failure_code)
    elif oris_called:
        state.result = INCONSISTENT_RESULT
        state.failure_code = "oris_called_without_control_tool"
        state.next_action = "FIX_CONTROL_TOOL_SELECTION_OR_TELEMETRY_CORRELATION"
        checks.fail_check("model_tool_call_capability", state.failure_code)
        checks.pass_check("oris_agent_harness_routing", "ORIS queue tool called")
    else:
        state.result = CAPABILITY_RESULT
        state.failure_code = "no_tool_call_observed"
        state.next_action = "DIAGNOSE_PROVIDER_MODEL_OR_GENERIC_AGENT_HARNESS"
        checks.fail_check("model_tool_call_capability", state.failure_code)
        checks.not_checked(
            "oris_agent_harness_routing",
            "generic tool-call capability was not demonstrated",
        )
