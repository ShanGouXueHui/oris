from __future__ import annotations

import tempfile
from pathlib import Path

from .agent_acceptance import run_automatic_acceptance
from .evidence import write_and_commit_evidence
from .gateway import (
    direct_readonly_probe,
    restart_gateway,
    verify_plugin_runtime,
    verify_public_routes,
)
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import (
    PolicyBackup,
    apply_readonly_policy,
    create_backup,
    finalize_marker,
    restore_denied_policy,
    validate_config_scope,
)
from .preflight_checks import run_transaction_preflight
from .skill import (
    SkillBackup,
    backup_routing_skill,
    install_routing_skill,
    restore_routing_skill,
)
from .state import (
    active_queue_count,
    listener_is_loopback_only,
    queue_fingerprint,
    repository_snapshot,
    repository_unchanged,
)


SUCCESS_RESULT = "ENABLED_READONLY_AUTOMATIC_ACCEPTED"


def _record_failure(state: RunState, checks: CheckRecorder, exc: Exception) -> None:
    state.result = "FAILED"
    state.failure_code = type(exc).__name__ + ":" + str(exc)
    state.next_action = "FIX_AUTOMATIC_ENABLEMENT_FAILURE_WITH_TOOLS_DENIED"
    checks.fail_check("automatic_enablement", type(exc).__name__)


def _commit_evidence(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
    temp_root: Path,
) -> tuple[str, str]:
    commit, evidence_log, evidence_json = write_and_commit_evidence(
        context,
        state,
        checks,
        stamp,
        temp_root,
    )
    state.evidence_commit = commit
    state.evidence_remote_verified = True
    return evidence_log, evidence_json


def _verify_runtime_boundaries(
    context: RuntimeContext,
    state: RunState,
    backup: PolicyBackup,
    oris_snapshot,
) -> None:
    validate_config_scope(context, backup, state.selected_policy_mode)
    runtime = verify_plugin_runtime(context)
    if not runtime.get("ok") or runtime.get("write_tools"):
        raise RuntimeError("final plugin runtime contract failed")
    if not all(listener_is_loopback_only(port) for port in context.internal_ports):
        raise RuntimeError("an internal listener exposure changed")
    if not verify_public_routes(context)["ok"]:
        raise RuntimeError("final public route contract failed")
    if not repository_unchanged(oris_snapshot, repository_snapshot(context.repo_root)):
        raise RuntimeError("ORIS primary worktree changed before evidence commit")


def _rollback(
    context: RuntimeContext,
    state: RunState,
    policy_backup: PolicyBackup | None,
    skill_backup: SkillBackup | None,
) -> None:
    if not state.mutation_started:
        return
    try:
        if policy_backup is not None:
            restore_denied_policy(context, policy_backup)
        if skill_backup is not None:
            restore_routing_skill(skill_backup)
        restart_gateway(context)
        state.rollback_count += 1
        state.rollback_healthy = "YES"
        state.mutation_started = False
        state.routing_skill_installed = False
    except Exception:
        state.rollback_healthy = "NO"


def run_enablement(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> tuple[str, str]:
    policy_backup: PolicyBackup | None = None
    skill_backup: SkillBackup | None = None
    evidence_log = ""
    evidence_json = ""
    try:
        baseline = run_transaction_preflight(context, checks)
        queue_before, baseline_tool, product_before, oris_before = baseline
        policy_backup = create_backup(context, stamp)
        skill_backup = backup_routing_skill(context, policy_backup.directory)
        checks.pass_check(
            "private_backup",
            "tools-denied config, marker, and routing skill backup captured",
        )

        state.mutation_started = True
        skill_details = install_routing_skill(context, skill_backup)
        state.routing_skill_installed = True
        state.details["routing_skill"] = skill_details
        checks.pass_check(
            "routing_skill",
            "managed ORIS read-only routing skill installed and effective",
        )

        state.selected_policy_mode = apply_readonly_policy(context, policy_backup)
        state.config_scope_valid = True
        restart_gateway(context)
        checks.pass_check(
            "controlled_policy_enablement",
            "minimal approved read-only policy applied",
        )

        if not verify_public_routes(context)["ok"]:
            raise RuntimeError("public routes failed after Gateway restart")
        runtime = verify_plugin_runtime(context)
        if not runtime.get("ok"):
            raise RuntimeError("plugin runtime contract failed after enablement")
        state.write_tools_absent = not runtime.get("write_tools")
        checks.pass_check(
            "plugin_runtime",
            "exact read-only tools and typed hooks verified",
        )

        direct = direct_readonly_probe(context, baseline_tool)
        state.details["direct_invocation"] = direct
        if not direct["ok"]:
            raise RuntimeError("direct approved read-only tool invocation failed")
        state.direct_tool_calls_pass = True
        checks.pass_check(
            "direct_tool_calls",
            "three ORIS tools and safe baseline tool passed",
        )

        if (
            queue_fingerprint(context.repo_root) != queue_before
            or active_queue_count(context.repo_root) != 0
        ):
            raise RuntimeError("queue changed during direct read-only tool calls")
        checks.pass_check("queue_after_direct_calls", "queue fingerprint is unchanged")

        automatic = run_automatic_acceptance(context, stamp)
        state.details["native_agent_acceptance"] = automatic
        if not automatic.get("accepted"):
            raise RuntimeError(
                str(
                    automatic.get("reason")
                    or "automatic native agent acceptance failed"
                )
            )
        state.native_agent_acceptance_pass = True
        telemetry = automatic.get("telemetry") or {}
        state.telemetry_privacy_pass = bool(
            telemetry.get("schema_ok")
            and telemetry.get("content_safe")
            and telemetry.get("only_approved_tools_used")
        )
        if not state.telemetry_privacy_pass:
            raise RuntimeError(
                "telemetry privacy, schema, or approved-tool validation failed"
            )
        checks.pass_check(
            "automatic_native_agent_acceptance",
            "three natural-language turns completed automatically",
        )
        checks.pass_check(
            "telemetry_privacy",
            "typed hook telemetry is private, schema-safe, and read-only",
        )

        if (
            queue_fingerprint(context.repo_root) != queue_before
            or active_queue_count(context.repo_root) != 0
        ):
            raise RuntimeError("queue changed during native agent acceptance")
        state.queue_unchanged = True
        checks.pass_check(
            "final_queue_invariant",
            "queue fingerprint and active count are unchanged",
        )

        if not repository_unchanged(
            product_before,
            repository_snapshot(context.product_repo),
        ):
            raise RuntimeError(
                "product repository changed during read-only acceptance"
            )
        state.product_unchanged = True
        checks.pass_check(
            "final_product_invariant",
            "product repository is unchanged",
        )

        _verify_runtime_boundaries(context, state, policy_backup, oris_before)
        checks.pass_check(
            "final_runtime_and_route_invariants",
            "runtime, routes, listeners, and worktree verified",
        )

        finalize_marker(context, policy_backup, state.selected_policy_mode, stamp)
        checks.pass_check(
            "private_marker",
            "automatic read-only acceptance recorded privately",
        )
        state.result = SUCCESS_RESULT
        state.failure_code = ""
        state.next_action = (
            "PERSIST_COMPLETION_AND_BEGIN_P1_TYPED_WRITE_ACTION_DESIGN"
        )
        state.rollback_healthy = "NOT_REQUIRED"
        evidence_log, evidence_json = _commit_evidence(
            context,
            state,
            checks,
            stamp,
            Path(tempfile.gettempdir()) / f"oris-enable-evidence-{stamp}",
        )
        state.mutation_started = False
        return evidence_log, evidence_json
    except Exception as exc:
        _record_failure(state, checks, exc)
        _rollback(context, state, policy_backup, skill_backup)
        try:
            evidence_log, evidence_json = _commit_evidence(
                context,
                state,
                checks,
                stamp,
                Path(tempfile.mkdtemp(prefix=f"oris-enable-evidence-{stamp}-")),
            )
        except Exception:
            state.evidence_commit = ""
            state.evidence_remote_verified = False
        return evidence_log, evidence_json
