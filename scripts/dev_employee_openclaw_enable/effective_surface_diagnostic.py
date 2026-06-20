from __future__ import annotations

import tempfile
from pathlib import Path

from .activation_candidate_gate import run_activation_candidate_gate
from .agent_skill_policy import resolve_default_agent_id
from .effective_tool_surface import probe_effective_tool_surface
from .enablement_activation import activate_candidate
from .enablement_rollback import run_enablement_rollback
from .evidence import write_and_commit_evidence
from .models import CheckRecorder, RepoSnapshot, RunState, RuntimeContext
from .plugin_runtime import verify_plugin_runtime
from .policy import PolicyBackup, create_backup
from .preflight_checks import run_transaction_preflight
from .skill_installation import SkillBackup, backup_routing_skill
from .state import (
    active_queue_count,
    listener_is_loopback_only,
    load_json,
    queue_fingerprint,
    repository_snapshot,
    repository_unchanged,
    sha256_file,
)


SUCCESS_RESULT = "EFFECTIVE_TOOL_SURFACE_VALIDATED_PENDING_EVIDENCE_REVIEW"
MISSING_RESULT = "EFFECTIVE_TOOL_SURFACE_MISSING_APPROVED_TOOLS"


def _commit_evidence(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> tuple[str, str]:
    root = Path(tempfile.mkdtemp(prefix=f"oris-effective-surface-{stamp}-"))
    commit, log_path, json_path = write_and_commit_evidence(
        context,
        state,
        checks,
        stamp,
        root,
    )
    state.evidence_commit = commit
    state.evidence_remote_verified = True
    return log_path, json_path


def _verify_final_invariants(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    queue_before: str,
    product_before: RepoSnapshot,
) -> None:
    queue_ok = (
        queue_fingerprint(context.repo_root) == queue_before
        and active_queue_count(context.repo_root) == 0
    )
    product_ok = repository_unchanged(
        product_before,
        repository_snapshot(context.product_repo),
    )
    listeners_ok = all(
        listener_is_loopback_only(port) for port in context.internal_ports
    )
    state.queue_unchanged = queue_ok
    state.product_unchanged = product_ok
    if queue_ok:
        checks.pass_check("final_queue_invariant", "queue remained unchanged")
    else:
        checks.fail_check("final_queue_invariant", "queue changed")
    if product_ok:
        checks.pass_check("final_product_invariant", "product repository remained unchanged")
    else:
        checks.fail_check("final_product_invariant", "product repository changed")
    if listeners_ok:
        checks.pass_check("final_listener_invariant", "internal listeners remained loopback-only")
    else:
        checks.fail_check("final_listener_invariant", "an internal listener became public")
    if not queue_ok or not product_ok or not listeners_ok:
        state.result = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_FAILED"
        state.failure_code = "final_invariant_failed"


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
        checks.not_checked(
            "effective_surface_rollback",
            "no active mutation occurred",
        )


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
        queue_before, _, product_before, _ = run_transaction_preflight(context, checks)
        gate = run_activation_candidate_gate(context, state, checks, stamp)
        validated_sha = gate.get("active_config_sha256")
        if not isinstance(validated_sha, str) or not validated_sha:
            raise RuntimeError("validated active configuration hash is unavailable")
        policy_backup = create_backup(context, stamp)
        if sha256_file(policy_backup.config_file) != validated_sha:
            raise RuntimeError("validated config differs from private backup")
        checks.pass_check(
            "effective_surface_snapshot",
            "validated active configuration exactly matches private backup",
        )
        skill_backup = backup_routing_skill(context, policy_backup.directory)
        checks.pass_check(
            "effective_surface_private_backup",
            "config, marker, and routing Skill backup captured",
        )
        application = activate_candidate(
            context,
            state,
            checks,
            policy_backup,
            skill_backup,
            validated_sha,
        )
        state.selected_policy_mode = application.mode

        runtime = verify_plugin_runtime(context)
        state.details["effective_surface_plugin_runtime"] = runtime
        state.write_tools_absent = not bool(runtime.get("write_tools"))
        if not runtime.get("ok") or not state.write_tools_absent:
            raise RuntimeError("plugin runtime contract failed before effective inventory")
        checks.pass_check(
            "effective_surface_plugin_runtime",
            "exact read-only plugin tools and hooks verified",
        )

        config = load_json(context.openclaw_config)
        agent_id = resolve_default_agent_id(config)
        surface = probe_effective_tool_surface(
            context,
            context.direct_probe_session_key,
            agent_id,
        )
        state.details["effective_tool_surface"] = surface
        if surface.get("status") == "PASS":
            checks.pass_check(
                "effective_tool_surface",
                "all approved ORIS tools are present and plugin-owned",
            )
            state.result = SUCCESS_RESULT
            state.failure_code = ""
            state.next_action = "READ_EFFECTIVE_SURFACE_EVIDENCE_BEFORE_MODEL_DIAGNOSIS"
        else:
            checks.fail_check(
                "effective_tool_surface",
                str(surface.get("reason_code") or "effective_surface_failed"),
            )
            state.result = MISSING_RESULT
            state.failure_code = str(
                surface.get("reason_code") or "effective_surface_failed"
            )
            state.next_action = "REMEDIATE_EFFECTIVE_TOOL_MATERIALIZATION"
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
            _verify_final_invariants(
                context,
                state,
                checks,
                queue_before,
                product_before,
            )
        if state.rollback_healthy == "NO":
            state.result = "EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_FAILED"
            state.failure_code = "rollback_failed"
            state.next_action = "RESTORE_TOOLS_DENIED_BASELINE"
        try:
            evidence_log, evidence_json = _commit_evidence(
                context,
                state,
                checks,
                stamp,
            )
        except Exception:
            state.evidence_commit = ""
            state.evidence_remote_verified = False
    return evidence_log, evidence_json
