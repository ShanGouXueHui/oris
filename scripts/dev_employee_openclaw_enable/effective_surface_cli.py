from __future__ import annotations

from .clock import utc_compact_stamp
from .code_audit_cli import audit_code_state
from .context import discover_repo_root, load_context
from .effective_surface_diagnostic import (
    SUCCESS_RESULT,
    run_effective_surface_diagnostic,
)
from .models import CheckRecorder, RunState, RuntimeContext
from .reporting import print_summary


def main() -> int:
    state = RunState()
    checks = CheckRecorder()
    context: RuntimeContext | None = None
    evidence_log = ""
    evidence_json = ""

    audit, _, contract_error = audit_code_state(discover_repo_root())
    if not audit.get("ok"):
        state.result = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_BLOCKED"
        state.failure_code = contract_error or "code_audit_findings"
        state.next_action = "FIX_ALL_CODE_AUDIT_FINDINGS"
        checks.fail_check(
            "code_audit_gate",
            "runtime diagnostic blocked before OpenClaw access",
        )
        print_summary(context, state, checks, evidence_log, evidence_json)
        return 2
    checks.pass_check(
        "code_audit_gate",
        "exact main revision passed the static code-first gate",
    )

    try:
        context = load_context()
        evidence_log, evidence_json = run_effective_surface_diagnostic(
            context,
            state,
            checks,
            utc_compact_stamp(),
        )
    except Exception as exc:
        state.result = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_FAILED"
        state.failure_code = type(exc).__name__
        state.next_action = "FIX_EFFECTIVE_SURFACE_DIAGNOSTIC_BOOTSTRAP"
        checks.fail_check("context_or_bootstrap", type(exc).__name__)
    print_summary(context, state, checks, evidence_log, evidence_json)
    return 0 if state.result == SUCCESS_RESULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
