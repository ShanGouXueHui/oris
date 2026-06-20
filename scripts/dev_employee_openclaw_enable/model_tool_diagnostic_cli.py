from __future__ import annotations

from .clock import utc_compact_stamp
from .code_audit_cli import audit_code_state
from .context import discover_repo_root, load_context
from .model_tool_diagnostic_contract import load_model_tool_diagnostic_contract
from .model_tool_diagnostic_result import PASS_RESULT
from .model_tool_diagnostic_runtime import run_model_tool_diagnostic
from .models import CheckRecorder, RunState, RuntimeContext
from .reporting import print_summary


def main() -> int:
    state = RunState()
    checks = CheckRecorder()
    context: RuntimeContext | None = None
    evidence_log = ""
    evidence_json = ""
    repo_root = discover_repo_root()
    audit, _, contract_error = audit_code_state(repo_root)
    if not audit.get("ok"):
        state.result = "MODEL_TOOL_DIAGNOSTIC_BLOCKED"
        state.failure_code = contract_error or "code_audit_findings"
        state.next_action = "FIX_ALL_CODE_AUDIT_FINDINGS"
        checks.fail_check("code_audit_gate", "blocked before OpenClaw access")
        print_summary(context, state, checks, evidence_log, evidence_json)
        return 2
    checks.pass_check("code_audit_gate", "exact main revision passed")
    try:
        context = load_context()
        contract = load_model_tool_diagnostic_contract(repo_root)
        evidence_log, evidence_json = run_model_tool_diagnostic(
            context,
            contract,
            state,
            checks,
            utc_compact_stamp(),
        )
    except Exception as exc:
        state.result = "MODEL_TOOL_DIAGNOSTIC_BOOTSTRAP_FAILED"
        state.failure_code = type(exc).__name__
        state.next_action = "FIX_MODEL_TOOL_DIAGNOSTIC_BOOTSTRAP"
        checks.fail_check("diagnostic_bootstrap", type(exc).__name__)
    print_summary(context, state, checks, evidence_log, evidence_json)
    return 0 if state.result == PASS_RESULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
