from __future__ import annotations

from dataclasses import dataclass

from .activation_candidate_gate import run_activation_candidate_gate
from .enablement_activation import activate_candidate
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import PolicyApplication, PolicyBackup, create_backup
from .skill_installation import SkillBackup, backup_routing_skill
from .state import sha256_file


@dataclass(frozen=True)
class ActivatedCandidate:
    policy_backup: PolicyBackup
    skill_backup: SkillBackup
    application: PolicyApplication


def activate_validated_candidate(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> ActivatedCandidate:
    gate = run_activation_candidate_gate(context, state, checks, stamp)
    validated_sha = gate.get("active_config_sha256")
    if not isinstance(validated_sha, str) or not validated_sha:
        raise RuntimeError("validated active configuration hash is unavailable")

    policy_backup = create_backup(context, stamp)
    if sha256_file(policy_backup.config_file) != validated_sha:
        raise RuntimeError("active configuration changed after candidate validation")
    checks.pass_check(
        "activation_candidate_snapshot",
        "validated active configuration exactly matches private backup",
    )

    skill_backup = backup_routing_skill(context, policy_backup.directory)
    checks.pass_check(
        "private_backup",
        "tools-denied config, marker, and routing Skill backup captured",
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
    return ActivatedCandidate(policy_backup, skill_backup, application)
