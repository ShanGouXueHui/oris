from __future__ import annotations

from datetime import datetime, timezone

from .context import load_context
from .models import CheckRecorder, RunState, RuntimeContext
from .reporting import print_summary
from .runner import SUCCESS_RESULT, run_enablement


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    state = RunState()
    checks = CheckRecorder()
    context: RuntimeContext | None = None
    evidence_log = ""
    evidence_json = ""
    try:
        context = load_context()
        evidence_log, evidence_json = run_enablement(
            context,
            state,
            checks,
            _stamp(),
        )
    except Exception as exc:
        state.result = "FAILED"
        state.failure_code = type(exc).__name__ + ":" + str(exc)
        checks.fail_check("context_or_bootstrap", type(exc).__name__)
    print_summary(context, state, checks, evidence_log, evidence_json)
    return 0 if state.result == SUCCESS_RESULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
