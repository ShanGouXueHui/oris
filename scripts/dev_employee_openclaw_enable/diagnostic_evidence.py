from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .evidence import write_and_commit_evidence
from .models import CheckRecorder, RunState, RuntimeContext, stage_status


def publish_diagnostic_evidence(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
    temp_root: Path,
) -> tuple[str, str, str]:
    state.details["diagnostic_stage_status"] = {
        "direct_tool_calls": stage_status(state.direct_tool_calls_pass),
        "native_agent_acceptance": stage_status(
            state.native_agent_acceptance_pass
        ),
        "telemetry_privacy": stage_status(state.telemetry_privacy_pass),
        "config_scope": stage_status(state.config_scope_valid),
        "queue_unchanged": stage_status(state.queue_unchanged),
        "product_unchanged": stage_status(state.product_unchanged),
        "write_tools_absent": stage_status(state.write_tools_absent),
    }
    state.details["diagnostic_check_summary"] = {
        "total": len(checks.checks),
        "pass": checks.pass_count,
        "fail": checks.fail_count,
        "not_checked": checks.not_checked_count,
    }
    diagnostic_context = replace(
        context,
        evidence_commit_prefix=(
            "chore(dev-employee): record OpenClaw read-only policy diagnostic"
        ),
    )
    return write_and_commit_evidence(
        diagnostic_context,
        state,
        checks,
        stamp,
        temp_root,
    )
