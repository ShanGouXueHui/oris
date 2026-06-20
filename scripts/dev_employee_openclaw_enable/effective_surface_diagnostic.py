from __future__ import annotations

import tempfile
from pathlib import Path

from .activation_transaction import activate_validated_candidate
from .agent_skill_policy import resolve_default_agent_id
from .effective_surface_inventory import probe_approved_effective_tool_surface
from .enablement_rollback import run_enablement_rollback
from .evidence import publish_evidence
from .models import CheckRecorder, RepoSnapshot, RunState, RuntimeContext
from .plugin_runtime import verify_plugin_runtime
from .policy import PolicyBackup
from .preflight_checks import run_transaction_preflight
from .readonly_invariants import evaluate_readonly_invariants, record_readonly_invariants
from .skill_installation import SkillBackup
from .state import load_json


SUCCESS_RESULT = "EFFECTIVE_TOOL_SURFACE_VALIDATED_PENDING_EVIDENCE_REVIEW"
MISSING_RESULT = "EFFECTIVE_TOOL_SURFACE_MISSING_APPROVED_TOOLS"
UNAVAILABLE_RESULT = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_UNAVAILABLE"
_UNAVAILABLE_REASONS = {
    "tools_effective_rpc_failed",
    "tools_effective_payload_invalid",
}


def _record_rollback_check(state: RunState, checks: CheckRecorder) -> None:
    if state.rollback_healthy == "YES":
        checks.pass_check(
            "effective_surface_rollback",
            "exact tools-denied baseline and healthy Gateway restored",
        )
    elif state.rollback_healthy == "NO":
        checks.fail_check(
            "effective_surface_rollback",
            "rollback did not restore the complete healthy baseline",
        )
    else:
        checks.not_checked("effective_surface_rollback", "no active mutation occurred")


def _record_surface_result(
    state: RunState,
    checks: CheckRecorder,
    surface: dict[str, object],
) -> None:
    state.details["effective_tool_surface"] = surface
    if surface.get("status") == "PASS":
        checks.pass_check(
            "effective_tool_surface",
            "all approved ORIS tools are present and plugin-owned",
        )
        state.result = SUCCESS_RESULT
        state.failure_code = ""
        state.next_action = "READ_EFFECTIVE_SURFACE_EVIDENCE_BEFORE_MODEL_DIAGNOSIS"
        return
    reason = str(surface.get("reason_code") or "effective_surface_failed")
    checks.fail_check("effective_tool_surface", reason)
    state.failure_code = reason
    if reason in _UNAVAILABLE_REASONS:
        state.result = UNAVAILABLE_RESULT
        state.next_action = "REPAIR_NATIVE_EFFECTIVE_SURFACE_DIAGNOSTIC_PATH"
    else:
        state.result = MISSING_RESULT
        state.next_action = "REMEDIATE_EFFECTIVE_TOOL_MATERIALIZATION"


def _record_missing_final_baseline(checks: CheckRecorder) -> None:
    for name in (
        "final_queue_invariant",
        "final_product_invariant",
        "final_listener_invariant",
    ):
        checks.not_checked(name, "baseline capture failed before runtime mutation")


def run_effective_surface_diagnostic(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> tuple[str, str]:
    policy_backup: PolicyBackup | None = None
    skill_backup: SkillBackup | None = None
    queue_before = ""
    product_before: RepoSnapshot | None = None
    evidence_log = ""
    evidence_json = ""
    try:
        queue_before, _, product_before, _ = run_transaction_preflight(
            context,
            checks,
            probe_safe_builtin=False,
        )
        activation = activate_validated_candidate(context, state, checks, stamp)
        policy_backup = activation.policy_backup
        skill_backup = activation.skill_backup

        runtime = verify_plugin_runtime(context)
        state.details["effective_surface_plugin_runtime"] = {
            "ok": runtime.get("ok") is True,
            "plugin_found": runtime.get("plugin_found") is True,
            "plugin_enabled": runtime.get("plugin_enabled") is True,
            "plugin_version_ok": runtime.get("plugin_version_ok") is True,
            "plugin_error_count": int(runtime.get("plugin_error_count") or 0),
            "approved_tool_count": len(runtime.get("tools") or []),
            "required_hook_count": len(runtime.get("hooks") or []),
            "write_tool_count": len(runtime.get("write_tools") or []),
            "non_approved_tool_names_recorded": False,
            "hook_names_recorded": False,
        }
        state.write_tools_absent = not bool(runtime.get("write_tools"))
        if not runtime.get("ok") or not state.write_tools_absent:
            raise RuntimeError("plugin runtime contract failed before effective inventory")
        checks.pass_check(
            "effective_surface_plugin_runtime",
            "exact read-only plugin tools and hooks verified",
        )

        config = load_json(context.openclaw_config)
        agent_id = resolve_default_agent_id(config)
        surface = probe_approved_effective_tool_surface(
            context,
            context.direct_probe_session_key,
            agent_id,
        )
        _record_surface_result(state, checks, surface)
        checks.not_checked(
            "native_agent_acceptance",
            "model turns are prohibited in this diagnostic",
        )
        checks.not_checked(
            "telemetry_acceptance",
            "no model or ORIS tool invocation is permitted",
        )
    except Exception as exc:
        state.result = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_FAILED"
        state.failure_code = type(exc).__name__
        state.next_action = "READ_EFFECTIVE_SURFACE_FAILURE_EVIDENCE"
        checks.fail_check("effective_surface_diagnostic", type(exc).__name__)
    finally:
        run_enablement_rollback(context, state, policy_backup, skill_backup)
        _record_rollback_check(state, checks)
        if product_before is not None and queue_before:
            invariants = evaluate_readonly_invariants(
                context,
                queue_before,
                product_before,
            )
            record_readonly_invariants(state, checks, invariants)
            if not invariants.ok:
                state.result = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_FAILED"
                state.failure_code = "final_invariant_failed"
                state.next_action = "RESTORE_TOOLS_DENIED_BASELINE"
        else:
            _record_missing_final_baseline(checks)
        if state.rollback_healthy == "NO":
            state.result = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_FAILED"
            state.failure_code = "rollback_failed"
            state.next_action = "RESTORE_TOOLS_DENIED_BASELINE"
        try:
            evidence_log, evidence_json = publish_evidence(
                context,
                state,
                checks,
                stamp,
                Path(tempfile.mkdtemp(prefix=f"oris-effective-surface-{stamp}-")),
                context.effective_surface_evidence,
            )
            checks.pass_check(
                "effective_surface_evidence",
                "sanitized detached-worktree evidence published and remote-verified",
            )
        except Exception as exc:
            state.evidence_commit = ""
            state.evidence_remote_verified = False
            state.result = "EFFECTIVE_TOOL_SURFACE_EVIDENCE_PUBLISH_FAILED"
            state.failure_code = type(exc).__name__
            state.next_action = (
                "FIX_EVIDENCE_PUBLICATION_WITHOUT_REPEATING_RUNTIME_DIAGNOSTIC"
            )
            checks.fail_check("effective_surface_evidence", type(exc).__name__)
    return evidence_log, evidence_json
