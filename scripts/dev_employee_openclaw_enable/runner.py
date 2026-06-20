from __future__ import annotations

import tempfile
from pathlib import Path

from .enablement_acceptance import (
    finalize_enablement,
    run_native_acceptance,
    verify_final_invariants,
)
from .enablement_activation import activate_candidate, verify_runtime_and_direct_calls
from .evidence import write_and_commit_evidence
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import PolicyApplication, PolicyBackup, create_backup, restore_denied_policy
from .preflight_checks import run_transaction_preflight
from .service_control import GatewayServiceError, restart_service_and_wait
from .skill_installation import SkillBackup, backup_routing_skill, restore_routing_skill


SUCCESS_RESULT = "ENABLED_READONLY_AUTOMATIC_ACCEPTED"


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
        state.details["rollback_gateway_restart"] = restart_service_and_wait(context)
        state.rollback_count += 1
        state.rollback_healthy = "YES"
        state.mutation_started = False
        state.routing_skill_installed = False
    except GatewayServiceError as exc:
        state.details["rollback_gateway_failure_diagnostics"] = exc.safe_evidence
        state.rollback_healthy = "NO"
    except Exception:
        state.rollback_healthy = "NO"


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
        policy_backup = create_backup(context, stamp)
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
