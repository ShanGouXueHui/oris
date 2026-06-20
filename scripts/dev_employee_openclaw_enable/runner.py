from __future__ import annotations

import tempfile
from pathlib import Path

from .activation_transaction import activate_validated_candidate
from .enablement_acceptance import finalize_enablement, run_native_acceptance, verify_final_invariants
from .enablement_activation import verify_runtime_and_direct_calls
from .enablement_rollback import run_enablement_rollback
from .evidence import publish_evidence
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import PolicyApplication, PolicyBackup
from .preflight_checks import run_transaction_preflight
from .skill_installation import SkillBackup


SUCCESS_RESULT = "ENABLED_READONLY_AUTOMATIC_ACCEPTED"
_STAGES = (
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


def _mark_unchecked(checks: CheckRecorder) -> None:
    recorded = {str(item.get("name")) for item in checks.checks}
    for name in _STAGES:
        if name not in recorded:
            checks.not_checked(name, "blocked by an earlier enablement failure")


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
        queue_before, baseline_tool, product_before, oris_before = run_transaction_preflight(context, checks)
        activation = activate_validated_candidate(context, state, checks, stamp)
        policy_backup = activation.policy_backup
        skill_backup = activation.skill_backup
        application = activation.application
        verify_runtime_and_direct_calls(context, state, checks, baseline_tool, queue_before)
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
        finalize_enablement(context, state, checks, policy_backup, application, stamp)
        state.result = SUCCESS_RESULT
        state.failure_code = ""
        state.next_action = "ESTABLISH_PRIVACY_SAFE_LATENCY_BASELINE"
        state.rollback_healthy = "NOT_REQUIRED"
        evidence_log, evidence_json = publish_evidence(
            context,
            state,
            checks,
            stamp,
            Path(tempfile.gettempdir()) / f"oris-enable-evidence-{stamp}",
            context.enablement_evidence,
        )
        state.mutation_started = False
    except Exception as exc:
        state.result = "FAILED"
        state.failure_code = type(exc).__name__
        state.next_action = "FIX_ENABLEMENT_FAILURE_WITH_TOOLS_DENIED"
        checks.fail_check("automatic_enablement", type(exc).__name__)
        _mark_unchecked(checks)
        run_enablement_rollback(context, state, policy_backup, skill_backup)
        try:
            evidence_log, evidence_json = publish_evidence(
                context,
                state,
                checks,
                stamp,
                Path(tempfile.mkdtemp(prefix=f"oris-enable-evidence-{stamp}-")),
                context.enablement_evidence,
            )
        except Exception:
            state.evidence_commit = ""
            state.evidence_remote_verified = False
    return evidence_log, evidence_json
