from __future__ import annotations

from .clock import utc_compact_stamp
from .context import load_context
from .diagnostic import SUCCESS_RESULT, run_policy_diagnostic
from .models import CheckRecorder, RunState, RuntimeContext
from .reporting import print_summary


def main() -> int:
    state = RunState()
    checks = CheckRecorder()
    context: RuntimeContext | None = None
    evidence_log = ""
    evidence_json = ""
    try:
        context = load_context()
        evidence_log, evidence_json = run_policy_diagnostic(
            context,
            state,
            checks,
            utc_compact_stamp(),
        )
    except Exception as exc:
        state.result = "DIAGNOSTIC_BOOTSTRAP_FAILED"
        state.failure_code = type(exc).__name__
        state.next_action = "FIX_DIAGNOSTIC_BOOTSTRAP_WITHOUT_RUNNING_ENABLEMENT"
        checks.fail_check("diagnostic_bootstrap", type(exc).__name__)
    print_summary(context, state, checks, evidence_log, evidence_json)
    return 0 if state.result == SUCCESS_RESULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
