from __future__ import annotations

from .models import CheckRecorder, RunState, RuntimeContext


def print_summary(
    context: RuntimeContext | None,
    state: RunState,
    checks: CheckRecorder,
    evidence_log: str,
    evidence_json: str,
) -> None:
    print("===== SUMMARY =====")
    print(f"RESULT={state.result}")
    print(f"TASK_ID={context.task_id if context else ''}")
    print(f"FAILURE_CODE={state.failure_code}")
    print(f"SELECTED_POLICY_MODE={state.selected_policy_mode}")
    print(f"CHECKS_TOTAL={len(checks.checks)}")
    print(f"CHECKS_PASS={checks.pass_count}")
    print(f"CHECKS_FAIL={checks.fail_count}")
    print(f"DIRECT_TOOL_CALLS_PASS={'YES' if state.direct_tool_calls_pass else 'NO'}")
    print(f"NATIVE_AGENT_ACCEPTANCE_PASS={'YES' if state.native_agent_acceptance_pass else 'NO'}")
    print(f"TELEMETRY_PRIVACY_PASS={'YES' if state.telemetry_privacy_pass else 'NO'}")
    print(f"CONFIG_SCOPE_VALID={'YES' if state.config_scope_valid else 'NO'}")
    print(f"QUEUE_UNCHANGED={'YES' if state.queue_unchanged else 'NO'}")
    print(f"PRODUCT_UNCHANGED={'YES' if state.product_unchanged else 'NO'}")
    print(f"WRITE_TOOLS_ABSENT={'YES' if state.write_tools_absent else 'NO'}")
    print(f"ROLLBACK_COUNT={state.rollback_count}")
    print(f"ROLLBACK_HEALTHY={state.rollback_healthy}")
    print("PRODUCT_TASK_SUBMITTED=NO")
    print("WRITE_TOOLS_ADDED=NO")
    print("OPENCLAW_REINSTALLED_OR_UPGRADED=NO")
    print(f"EVIDENCE_LOG={evidence_log}")
    print(f"EVIDENCE_JSON={evidence_json}")
    print(f"EVIDENCE_COMMIT={state.evidence_commit}")
    print(f"EVIDENCE_REMOTE_VERIFIED={'YES' if state.evidence_remote_verified else 'NO'}")
    print(f"NEXT_ACTION={state.next_action}")
    print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
    print("===== END SUMMARY =====")
