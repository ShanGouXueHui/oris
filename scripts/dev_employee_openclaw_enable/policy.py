from __future__ import annotations

import copy
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_skill_policy import (
    AgentSkillPolicyChange,
    ensure_skill_visible,
    skill_is_visible,
    strip_authorized_skill_addition,
)
from .models import RuntimeContext
from .state import load_json


@dataclass(frozen=True)
class PolicyBackup:
    directory: Path
    config_file: Path
    marker_file: Path
    original_config: dict[str, Any]


@dataclass(frozen=True)
class PolicyApplication:
    tool_mode: str
    skill_policy: AgentSkillPolicyChange

    @property
    def mode(self) -> str:
        return f"{self.tool_mode}+{self.skill_policy.mode}"

    def evidence(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "tool_mode": self.tool_mode,
            "skill_policy": self.skill_policy.evidence(),
            "secret_values_recorded": False,
        }


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def validate_denied_baseline(context: RuntimeContext) -> dict[str, Any]:
    config = load_json(context.openclaw_config)
    tools = config.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy is missing")
    deny = tools.get("deny")
    if not isinstance(deny, list) or not all(isinstance(item, str) for item in deny):
        raise RuntimeError("OpenClaw tools.deny is not a string list")
    allow = tools.get("allow")
    if allow is not None and not (
        isinstance(allow, list) and all(isinstance(item, str) for item in allow)
    ):
        raise RuntimeError("OpenClaw tools.allow is not a string list")
    approved = set(context.approved_tools)
    if not approved.issubset(set(deny)):
        raise RuntimeError("approved tools are not all in the denied baseline")
    if tools.get("profile") != context.required_profile:
        raise RuntimeError("OpenClaw tool profile differs from the approved profile")
    return {
        "profile": tools.get("profile"),
        "allow_present": allow is not None,
        "allow_count": len(allow or []),
        "deny_count": len(deny),
        "approved_denied": sorted(approved.intersection(deny)),
    }


def create_backup(context: RuntimeContext, stamp: str) -> PolicyBackup:
    directory = context.backup_root / f"readonly-tool-enable-{stamp}"
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(directory, 0o700)
    config_file = directory / "openclaw.json.tools-denied.bak"
    marker_file = directory / "oris-plugin-marker.tools-denied.bak"
    shutil.copy2(context.openclaw_config, config_file)
    shutil.copy2(context.marker_file, marker_file)
    os.chmod(config_file, 0o600)
    os.chmod(marker_file, 0o600)
    return PolicyBackup(
        directory=directory,
        config_file=config_file,
        marker_file=marker_file,
        original_config=load_json(config_file),
    )


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def _apply_tool_policy(
    context: RuntimeContext,
    config: dict[str, Any],
) -> str:
    tools = config.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy is missing")
    deny = tools.get("deny")
    if not isinstance(deny, list):
        raise RuntimeError("OpenClaw tools.deny is invalid")
    approved = list(context.approved_tools)
    existing_allow = tools.get("allow")
    if existing_allow is None:
        mode = "materialized-profile-plus-approved"
        new_allow = _deduplicate([*context.profile_expansion, *approved])
    elif isinstance(existing_allow, list) and all(
        isinstance(item, str) for item in existing_allow
    ):
        mode = "preserved-allow-plus-approved"
        new_allow = _deduplicate([*existing_allow, *approved])
    else:
        raise RuntimeError("OpenClaw tools.allow is invalid")
    tools["allow"] = new_allow
    tools["deny"] = [item for item in deny if item not in set(approved)]
    return mode


def apply_readonly_policy(
    context: RuntimeContext,
    backup: PolicyBackup,
) -> PolicyApplication:
    config = load_json(backup.config_file)
    tool_mode = _apply_tool_policy(context, config)
    skill_policy = ensure_skill_visible(config, context.routing_skill_name)
    application = PolicyApplication(tool_mode, skill_policy)
    _atomic_write_json(context.openclaw_config, config)
    validate_config_scope(context, backup, application)
    return application


def _without_tool_allow_deny(value: dict[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(value)
    tools = copied.get("tools")
    if isinstance(tools, dict):
        tools.pop("allow", None)
        tools.pop("deny", None)
    return copied


def validate_config_scope(
    context: RuntimeContext,
    backup: PolicyBackup,
    application: PolicyApplication,
) -> None:
    before = _without_tool_allow_deny(backup.original_config)
    after_raw = load_json(context.openclaw_config)
    after = _without_tool_allow_deny(after_raw)
    after = strip_authorized_skill_addition(
        after,
        application.skill_policy,
        context.routing_skill_name,
    )
    if before != after:
        raise RuntimeError(
            "OpenClaw configuration changed outside approved tool and skill policy"
        )

    tools = after_raw.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy disappeared")
    if any(tool in set(tools.get("deny") or []) for tool in context.approved_tools):
        raise RuntimeError("an approved tool remains denied")
    allow = tools.get("allow")
    if not isinstance(allow, list):
        raise RuntimeError("OpenClaw tools.allow is missing after enablement")
    if not set(context.approved_tools).issubset(set(allow)):
        raise RuntimeError("an approved tool is absent from tools.allow")
    if application.tool_mode == "materialized-profile-plus-approved" and not set(
        context.profile_expansion
    ).issubset(set(allow)):
        raise RuntimeError("materialized profile expansion is incomplete")
    if not skill_is_visible(
        after_raw,
        context.routing_skill_name,
        application.skill_policy.agent_id,
    ):
        raise RuntimeError("routing skill is not visible to the default agent")


def restore_denied_policy(context: RuntimeContext, backup: PolicyBackup) -> None:
    shutil.copy2(backup.config_file, context.openclaw_config)
    shutil.copy2(backup.marker_file, context.marker_file)
    os.chmod(context.openclaw_config, 0o600)
    os.chmod(context.marker_file, 0o600)
    validate_denied_baseline(context)


def finalize_marker(
    context: RuntimeContext,
    backup: PolicyBackup,
    application: PolicyApplication,
    stamp: str,
) -> None:
    marker = load_json(context.marker_file)
    marker["state"] = "installed_readonly_tools_enabled"
    marker["readonly_enablement"] = {
        "policy_mode": application.mode,
        "tools_denied_backup": str(backup.config_file),
        "routing_skill": context.routing_skill_name,
        "routing_skill_scope": "managed_global",
        "routing_skill_agent": application.skill_policy.agent_id,
        "routing_skill_allowlist_scope": application.skill_policy.scope,
        "enabled_at": stamp,
        "write_tools_present": False,
        "automatic_native_agent_acceptance": True,
        "telemetry_privacy_pass": True,
    }
    _atomic_write_json(context.marker_file, marker)
