from __future__ import annotations

import tempfile
from pathlib import Path

from .activation_candidate_gate import run_activation_candidate_gate
from .enablement_acceptance import (
    finalize_enablement,
    run_native_acceptance,
    verify_final_invariants,
)
from .enablement_activation import activate_candidate, verify_runtime_and_direct_calls
from .enablement_rollback import run_enablement_rollback
from .evidence import write_and_commit_evidence
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import PolicyApplication, PolicyBackup, create_backup
from .preflight_checks import run_transaction_preflight
from .service_control import GatewayServiceError
from .skill_installation import SkillBackup, backup_routing_skill
from .state import sha256_file


SUCCESS_RESULT = "ENABLED_READONLY_AUTOMATIC_ACCEPTED"
_ENABLEMENT_STAGES = (
    "source_code_governance",
    "automatic_selftests",
    "authoritative_readiness",
    "tools_denied_baseline",
    "gateway_and_routes",
    "private_internal_listeners",
    "queue_baseline",
    "product_baseline",
    "oris_source_baseline",
    "safe_builtin_baseline",
    "activation_candidate_gate",
    "activation_candidate_snapshot",
    "private_backup",
    "routing_skill",
    "controlled_policy_enablement",
    "routing_skill_runtime",
    "plugin_runtime",
    "direct_tool_calls",
    "queue_after_direct_calls",
    "automatic_native_agent_acceptance",
    "telemetry_privacy",
    "final_queue_invariant",
    "final_product_invariant",
    "final_runtime_and_route_invariants",
    "private_marker",
)


def _record_failure(state: RunState, checks: CheckRecorder, exc: Exception) -> None:
    state.result = "FAILED"
    state.failure_code = (
        f"GatewayServiceError:{exc.code}"
        if isinstance(exc, GatewayServiceError)
        else type(exc).__name__
    )
    state.next_action = "FIX_AUTOMATIC_ENABLEMENT_FAILURE_WITH_TOOLS_DENIED"
    if isinstance(exc, GatewayServiceError):
        state.details["gateway_failure_diagnostics"] = exc.safe_evidence
    checks.fail_check("automatic_enablement", type(exc).__name__)


def _mark_remaining_not_checked(checks: CheckRecorder) -> None:
    recorded = {str(item.get("name")) for item in checks.checks}
    for name in _ENABLEMENT_STAGES:
        if name not in recorded:
            checks.not_checked(name, "blocked by an earlier enablement failure")


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


def run_enablement(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> tuple[str, str]:
    policy_backup: PolicyBackup | None = None
    application: PolicyApplication | None = None
    skill_backup: SkillBackup | None = None
    evidence_log = ""
    evidence_json = ""
    try:
        queue_before, baseline_tool, product_before, oris_before = (
            run_transaction_preflight(context, checks)
        )
        activation_gate = run_activation_candidate_gate(
            context,
            state,
            checks,
            stamp,
        )
        validated_config_sha256 = activation_gate.get("active_config_sha256")
        if not isinstance(validated_config_sha256, str) or not validated_config_sha256:
            raise RuntimeError("validated active configuration hash is unavailable")
        policy_backup = create_backup(context, stamp)
        if sha256_file(policy_backup.config_file) != validated_config_sha256:
            raise RuntimeError(
                "active configuration changed after activation candidate validation"
            )
        checks.pass_check(
            "activation_candidate_snapshot",
            "validated active configuration exactly matches the private backup",
        )
        skill_backup = backup_routing_skill(context, policy_backup.directory)
        checks.pass_check(
            "private_backup",
            "tools-denied config, marker, and routing skill backup captured",
        )
        application = activate_candidate(
            context,
            state,
            checks,
            policy_backup,
            skill_backup,
            validated_config_sha256,
        )
        verify_runtime_and_direct_calls(
            context,
            state,
            checks,
            baseline_tool,
            queue_before,
        )
        run_native_acceptance(context, state, checks, stamp, queue_before)
        verify_final_invariants(
            context,
            state,
            checks,
            product_before,
            oris_before,
            policy_backup,
            application,
        )
        finalize_enablement(
            context,
            state,
            checks,
            policy_backup,
            application,
            stamp,
        )
        state.result = SUCCESS_RESULT
        state.failure_code = ""
        state.next_action = (
            "PERSIST_COMPLETION_AND_ESTABLISH_PRIVACY_SAFE_LATENCY_BASELINE"
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
        _mark_remaining_not_checked(checks)
        run_enablement_rollback(context, state, policy_backup, skill_backup)
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
