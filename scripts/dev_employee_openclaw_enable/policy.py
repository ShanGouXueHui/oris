from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import RuntimeContext
from .state import load_json


@dataclass(frozen=True)
class PolicyBackup:
    directory: Path
    config_file: Path
    marker_file: Path
    original_config: dict[str, Any]


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
    directory = Path.home() / ".openclaw" / "backups" / f"readonly-tool-enable-{stamp}"
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


def apply_readonly_policy(context: RuntimeContext, backup: PolicyBackup) -> str:
    config = load_json(backup.config_file)
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
    elif isinstance(existing_allow, list) and all(isinstance(item, str) for item in existing_allow):
        mode = "preserved-allow-plus-approved"
        new_allow = _deduplicate([*existing_allow, *approved])
    else:
        raise RuntimeError("OpenClaw tools.allow is invalid")
    tools["allow"] = new_allow
    tools["deny"] = [item for item in deny if item not in set(approved)]
    _atomic_write_json(context.openclaw_config, config)
    validate_config_scope(context, backup, mode)
    return mode


def _without_allow_deny(value: dict[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(value))
    tools = copied.get("tools")
    if isinstance(tools, dict):
        tools.pop("allow", None)
        tools.pop("deny", None)
    return copied


def validate_config_scope(
    context: RuntimeContext,
    backup: PolicyBackup,
    mode: str,
) -> None:
    before = backup.original_config
    after = load_json(context.openclaw_config)
    if _without_allow_deny(before) != _without_allow_deny(after):
        raise RuntimeError("OpenClaw configuration changed outside tools.allow/tools.deny")
    tools = after.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy disappeared")
    if any(tool in set(tools.get("deny") or []) for tool in context.approved_tools):
        raise RuntimeError("an approved tool remains denied")
    allow = tools.get("allow")
    if not isinstance(allow, list):
        raise RuntimeError("OpenClaw tools.allow is missing after enablement")
    if not set(context.approved_tools).issubset(set(allow)):
        raise RuntimeError("an approved tool is absent from tools.allow")
    if mode == "materialized-profile-plus-approved" and not set(context.profile_expansion).issubset(set(allow)):
        raise RuntimeError("materialized profile expansion is incomplete")


def restore_denied_policy(context: RuntimeContext, backup: PolicyBackup) -> None:
    shutil.copy2(backup.config_file, context.openclaw_config)
    shutil.copy2(backup.marker_file, context.marker_file)
    os.chmod(context.openclaw_config, 0o600)
    os.chmod(context.marker_file, 0o600)
    validate_denied_baseline(context)


def finalize_marker(context: RuntimeContext, backup: PolicyBackup, mode: str, stamp: str) -> None:
    marker = load_json(context.marker_file)
    marker["state"] = "installed_readonly_tools_enabled"
    marker["readonly_enablement"] = {
        "policy_mode": mode,
        "tools_denied_backup": str(backup.config_file),
        "enabled_at": stamp,
        "write_tools_present": False,
        "automatic_native_agent_acceptance": True,
        "telemetry_privacy_pass": True,
    }
    _atomic_write_json(context.marker_file, marker)
