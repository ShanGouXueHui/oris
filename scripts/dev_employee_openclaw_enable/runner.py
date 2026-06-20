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
from .evidence import write_and_commit_evidence
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import (
    PolicyApplication,
    PolicyBackup,
    create_backup,
    restore_denied_policy,
    validate_denied_baseline,
)
from .preflight_checks import run_transaction_preflight
from .service_control import (
    GatewayServiceError,
    restart_service_and_wait,
    service_snapshot,
)
from .skill_installation import SkillBackup, backup_routing_skill, restore_routing_skill
from .state import sha256_file


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
    policy_attempted = state.details.get("policy_config_write_attempted") is True
    skill_attempted = state.details.get("routing_skill_mutation_attempted") is True
    restart_attempted = (
        state.details.get("candidate_gateway_restart_attempted") is True
    )
    failures: list[str] = []

    if policy_attempted:
        if policy_backup is None:
            failures.append("policy_backup_unavailable")
        else:
            try:
                restore_denied_policy(context, policy_backup)
                state.details["rollback_policy_restored"] = True
            except Exception as exc:
                failures.append("policy_restore:" + type(exc).__name__)

    if skill_attempted:
        if skill_backup is None:
            failures.append("skill_backup_unavailable")
        else:
            try:
                restore_routing_skill(skill_backup)
                state.details["rollback_skill_restored"] = True
            except Exception as exc:
                failures.append("skill_restore:" + type(exc).__name__)

    if restart_attempted:
        try:
            state.details["rollback_gateway_restart"] = restart_service_and_wait(context)
        except GatewayServiceError as exc:
            failures.append("gateway_restart:" + exc.code)
            state.details["rollback_gateway_failure_diagnostics"] = exc.safe_evidence
        except Exception as exc:
            failures.append("gateway_restart:" + type(exc).__name__)
    else:
        state.details["rollback_gateway_restart"] = {
            "required": False,
            "reason": "candidate_gateway_restart_not_attempted",
        }

    try:
        state.details["rollback_denied_baseline"] = validate_denied_baseline(context)
    except Exception as exc:
        failures.append("denied_baseline:" + type(exc).__name__)
    final_gateway = service_snapshot(context)
    state.details["rollback_final_gateway"] = final_gateway.evidence()
    if not final_gateway.healthy:
        failures.append("gateway_final_health")

    state.rollback_count += 1
    state.details["rollback_failure_codes"] = failures
    state.rollback_healthy = "NO" if failures else "YES"
    if not failures:
        state.mutation_started = False
        state.routing_skill_installed = False


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
