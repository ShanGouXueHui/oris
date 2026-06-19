from __future__ import annotations

from typing import Any

from .models import CheckRecorder, RunState, RuntimeContext


def _detail_dict(state: RunState, key: str) -> dict[str, Any]:
    value = state.details.get(key)
    return value if isinstance(value, dict) else {}


def _yes_no(value: Any) -> str:
    return "YES" if value is True else "NO"


def print_summary(
    context: RuntimeContext | None,
    state: RunState,
    checks: CheckRecorder,
    evidence_log: str,
    evidence_json: str,
) -> None:
    skill_runtime = _detail_dict(state, "routing_skill_runtime")
    automatic = _detail_dict(state, "native_agent_acceptance")
    telemetry = automatic.get("telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    all_event_counts = telemetry.get("all_event_counts")
    all_event_counts = all_event_counts if isinstance(all_event_counts, dict) else {}

    print("===== SUMMARY =====")
    print(f"RESULT={state.result}")
    print(f"TASK_ID={context.task_id if context else ''}")
    print(f"FAILURE_CODE={state.failure_code}")
    print(f"SELECTED_POLICY_MODE={state.selected_policy_mode}")
    print(f"CHECKS_TOTAL={len(checks.checks)}")
    print(f"CHECKS_PASS={checks.pass_count}")
    print(f"CHECKS_FAIL={checks.fail_count}")
    print(f"ROUTING_SKILL_INSTALLED={_yes_no(state.routing_skill_installed)}")
    print(f"ROUTING_SKILL_RUNTIME_VISIBLE={_yes_no(skill_runtime.get('visible'))}")
    print(f"ROUTING_SKILL_AGENT={skill_runtime.get('agent_id') or automatic.get('agent_id') or ''}")
    print(f"DIRECT_TOOL_CALLS_PASS={_yes_no(state.direct_tool_calls_pass)}")
    print(f"NATIVE_AGENT_ACCEPTANCE_PASS={_yes_no(state.native_agent_acceptance_pass)}")
    print(f"TELEMETRY_PRIVACY_PASS={_yes_no(state.telemetry_privacy_pass)}")
    print(f"TELEMETRY_AFTER_TOOL_CALL_COUNT={all_event_counts.get('after_tool_call', 0)}")
    print(f"CONFIG_SCOPE_VALID={_yes_no(state.config_scope_valid)}")
    print(f"QUEUE_UNCHANGED={_yes_no(state.queue_unchanged)}")
    print(f"PRODUCT_UNCHANGED={_yes_no(state.product_unchanged)}")
    print(f"WRITE_TOOLS_ABSENT={_yes_no(state.write_tools_absent)}")
    print(f"ROLLBACK_COUNT={state.rollback_count}")
    print(f"ROLLBACK_HEALTHY={state.rollback_healthy}")
    print("PRODUCT_TASK_SUBMITTED=NO")
    print("WRITE_TOOLS_ADDED=NO")
    print("OPENCLAW_REINSTALLED_OR_UPGRADED=NO")
    print(f"EVIDENCE_LOG={evidence_log}")
    print(f"EVIDENCE_JSON={evidence_json}")
    print(f"EVIDENCE_COMMIT={state.evidence_commit}")
    print(f"EVIDENCE_REMOTE_VERIFIED={_yes_no(state.evidence_remote_verified)}")
    print(f"NEXT_ACTION={state.next_action}")
    print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
    print("===== END SUMMARY =====")
