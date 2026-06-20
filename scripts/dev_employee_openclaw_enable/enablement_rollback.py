from __future__ import annotations

from .models import RunState, RuntimeContext
from .policy import PolicyBackup, restore_denied_policy, validate_denied_baseline
from .service_control import (
    GatewayServiceError,
    restart_service_and_wait,
    service_snapshot,
)
from .skill_installation import SkillBackup, restore_routing_skill


def _restore_policy(
    context: RuntimeContext,
    state: RunState,
    backup: PolicyBackup | None,
    failures: list[str],
) -> None:
    if state.details.get("policy_config_write_attempted") is not True:
        return
    if backup is None:
        failures.append("policy_backup_unavailable")
        return
    try:
        restore_denied_policy(context, backup)
        state.details["rollback_policy_restored"] = True
    except Exception as exc:
        failures.append("policy_restore:" + type(exc).__name__)


def _restore_skill(
    state: RunState,
    backup: SkillBackup | None,
    failures: list[str],
) -> None:
    if state.details.get("routing_skill_mutation_attempted") is not True:
        return
    if backup is None:
        failures.append("skill_backup_unavailable")
        return
    try:
        restore_routing_skill(backup)
        state.details["rollback_skill_restored"] = True
    except Exception as exc:
        failures.append("skill_restore:" + type(exc).__name__)


def _restore_gateway(
    context: RuntimeContext,
    state: RunState,
    failures: list[str],
) -> None:
    if state.details.get("candidate_gateway_restart_attempted") is not True:
        state.details["rollback_gateway_restart"] = {
            "required": False,
            "reason": "candidate_gateway_restart_not_attempted",
        }
        return
    try:
        state.details["rollback_gateway_restart"] = restart_service_and_wait(context)
    except GatewayServiceError as exc:
        failures.append("gateway_restart:" + exc.code)
        state.details["rollback_gateway_failure_diagnostics"] = exc.safe_evidence
    except Exception as exc:
        failures.append("gateway_restart:" + type(exc).__name__)


def _verify_final_baseline(
    context: RuntimeContext,
    state: RunState,
    failures: list[str],
) -> None:
    try:
        state.details["rollback_denied_baseline"] = validate_denied_baseline(context)
    except Exception as exc:
        failures.append("denied_baseline:" + type(exc).__name__)
    gateway = service_snapshot(context)
    state.details["rollback_final_gateway"] = gateway.evidence()
    if not gateway.healthy:
        failures.append("gateway_final_health")


def run_enablement_rollback(
    context: RuntimeContext,
    state: RunState,
    policy_backup: PolicyBackup | None,
    skill_backup: SkillBackup | None,
) -> None:
    if not state.mutation_started:
        return
    failures: list[str] = []
    _restore_policy(context, state, policy_backup, failures)
    _restore_skill(state, skill_backup, failures)
    _restore_gateway(context, state, failures)
    _verify_final_baseline(context, state, failures)

    state.rollback_count += 1
    state.details["rollback_failure_codes"] = failures
    state.rollback_healthy = "NO" if failures else "YES"
    if not failures:
        state.mutation_started = False
        state.routing_skill_installed = False
