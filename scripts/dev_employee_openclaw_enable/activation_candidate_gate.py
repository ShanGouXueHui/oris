from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from .diagnostic_candidate import (
    build_private_candidate,
    candidate_evidence,
    inspect_private_candidate,
)
from .models import CheckRecorder, RunState, RuntimeContext
from .state import sha256_file


_AGENT_SKILL_PATH = re.compile(
    r"agents\.(?:defaults\.skills|list\[[0-9]+\]\.skills)"
)


def _required_tool_paths(application: dict[str, Any]) -> tuple[str, set[str]]:
    tool_policy = application.get("tool_policy")
    if not isinstance(tool_policy, dict):
        raise RuntimeError("candidate tool-policy evidence is unavailable")
    allow_added = tool_policy.get("allow_added_count")
    also_added = tool_policy.get("also_allow_added_count")
    if not isinstance(allow_added, int) or not isinstance(also_added, int):
        raise RuntimeError("candidate authorization counts are invalid")
    if allow_added > 0 and also_added > 0:
        raise RuntimeError("candidate activates allow and alsoAllow together")
    if allow_added > 0:
        return "allow", {"tools.allow", "tools.deny"}
    if also_added > 0:
        return "profile-plus-alsoAllow", {"tools.alsoAllow", "tools.deny"}
    raise RuntimeError("candidate does not add an approved tool authorization")


def _required_skill_path(application: dict[str, Any]) -> str | None:
    skill_policy = application.get("skill_policy")
    if not isinstance(skill_policy, dict):
        raise RuntimeError("candidate skill-policy evidence is unavailable")
    if skill_policy.get("changed") is not True:
        return None
    scope = skill_policy.get("scope")
    if scope == "defaults":
        return "agents.defaults.skills"
    if scope == "agent":
        return "agent-scoped-skill-path"
    raise RuntimeError("candidate skill-policy scope is invalid")


def validate_activation_candidate_result(
    application: dict[str, Any],
    compatibility: dict[str, Any],
    runtime_validation: dict[str, Any],
) -> dict[str, Any]:
    if compatibility.get("status") != "PASS":
        raise RuntimeError("candidate compatibility gate failed")
    checks = compatibility.get("checks")
    if not isinstance(checks, dict) or not all(
        checks.get(name) is True
        for name in (
            "profile_matches",
            "single_authorization_scope",
            "authorization_scope_present",
            "approved_authorized",
            "approved_removed_from_deny",
            "routing_skill_visible",
        )
    ):
        raise RuntimeError("candidate compatibility checks are incomplete")

    expected_scope, expected_paths = _required_tool_paths(application)
    if compatibility.get("authorization_scope") != expected_scope:
        raise RuntimeError("candidate authorization scope differs from policy evidence")

    skill_requirement = _required_skill_path(application)
    if runtime_validation.get("status") != "PASS":
        raise RuntimeError("installed runtime rejected the activation candidate")
    if runtime_validation.get("active_config_unchanged") is not True:
        raise RuntimeError("candidate dry-run changed the active configuration")
    if runtime_validation.get("active_config_written") is not False:
        raise RuntimeError("candidate dry-run reported an active configuration write")

    patch = runtime_validation.get("policy_patch")
    if not isinstance(patch, dict):
        raise RuntimeError("candidate policy-patch evidence is unavailable")
    changed_paths = patch.get("changed_paths")
    if not isinstance(changed_paths, list) or not all(
        isinstance(path, str) for path in changed_paths
    ):
        raise RuntimeError("candidate changed-path evidence is invalid")
    if len(changed_paths) != len(set(changed_paths)):
        raise RuntimeError("candidate changed-path evidence contains duplicates")

    actual_paths = set(changed_paths)
    agent_paths = {path for path in actual_paths if _AGENT_SKILL_PATH.fullmatch(path)}
    if skill_requirement is None and agent_paths:
        raise RuntimeError("candidate changes an unrequired agent Skill path")
    if skill_requirement == "agents.defaults.skills":
        expected_paths.add(skill_requirement)
    elif skill_requirement == "agent-scoped-skill-path":
        if len(agent_paths) != 1:
            raise RuntimeError("candidate agent Skill path is missing or ambiguous")
        expected_paths.update(agent_paths)
    if actual_paths != expected_paths:
        raise RuntimeError("candidate changes paths outside the approved policy delta")

    diagnostics = runtime_validation.get("validation_diagnostics")
    if not isinstance(diagnostics, dict):
        raise RuntimeError("runtime validation diagnostics are unavailable")
    diagnostic_checks = diagnostics.get("checks")
    if not isinstance(diagnostic_checks, dict) or not all(
        diagnostic_checks.get(name) is True
        for name in ("schema", "resolvability", "resolvabilityComplete")
    ):
        raise RuntimeError("runtime schema or resolvability validation is incomplete")
    if diagnostics.get("ok") is not True or diagnostics.get("error_count") != 0:
        raise RuntimeError("runtime validation diagnostics contain an error")
    if diagnostics.get("raw_output_recorded") is not False:
        raise RuntimeError("runtime validation retained raw output")
    if diagnostics.get("secret_refs_recorded") is not False:
        raise RuntimeError("runtime validation retained SecretRef identifiers")

    return {
        "status": "PASS",
        "authorization_scope": expected_scope,
        "changed_paths": sorted(actual_paths),
        "validator": runtime_validation.get("validator"),
        "active_config_unchanged": True,
        "active_config_written": False,
        "schema_validated": True,
        "resolvability_validated": True,
        "error_count": 0,
        "raw_output_recorded": False,
        "secret_refs_recorded": False,
        "candidate_config_recorded": False,
    }


def run_activation_candidate_gate(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> dict[str, Any]:
    active_sha = sha256_file(context.openclaw_config)
    with tempfile.TemporaryDirectory(
        prefix=f"oris-activation-candidate-{stamp}-"
    ) as directory:
        root = Path(directory)
        candidate_path, application = build_private_candidate(context, root)
        compatibility, runtime_validation = inspect_private_candidate(
            context,
            candidate_path,
        )
        result = validate_activation_candidate_result(
            application,
            compatibility,
            runtime_validation,
        )
        result["candidate"] = candidate_evidence(candidate_path)
    if sha256_file(context.openclaw_config) != active_sha:
        raise RuntimeError("active configuration changed during activation candidate gate")
    result["active_config_sha256"] = active_sha
    state.details["activation_candidate_gate"] = result
    checks.pass_check(
        "activation_candidate_gate",
        "single-scope candidate passed just-in-time native dry-run",
    )
    return result
