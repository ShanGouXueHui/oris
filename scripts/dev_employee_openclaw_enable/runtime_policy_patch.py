from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .models import RuntimeContext
from .state import load_json


_TOOL_POLICY_KEYS = ("profile", "allow", "alsoAllow", "deny")


def _changed_value(
    active: dict[str, Any],
    candidate: dict[str, Any],
    key: str,
) -> tuple[bool, Any]:
    active_present = key in active
    candidate_present = key in candidate
    if candidate_present:
        value = copy.deepcopy(candidate[key])
        return (not active_present or active.get(key) != value), value
    return active_present, None


def _agent_skill_patch(
    active: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    patch: dict[str, Any] = {}
    replace_paths: list[str] = []
    changed_paths: list[str] = []
    active_agents = active.get("agents")
    candidate_agents = candidate.get("agents")
    if not isinstance(active_agents, dict) or not isinstance(candidate_agents, dict):
        return patch, replace_paths, changed_paths

    active_defaults = active_agents.get("defaults")
    candidate_defaults = candidate_agents.get("defaults")
    if isinstance(active_defaults, dict) and isinstance(candidate_defaults, dict):
        changed, value = _changed_value(active_defaults, candidate_defaults, "skills")
        if changed:
            patch.setdefault("agents", {}).setdefault("defaults", {})["skills"] = value
            changed_paths.append("agents.defaults.skills")

    active_list = active_agents.get("list")
    candidate_list = candidate_agents.get("list")
    if not isinstance(active_list, list) or not isinstance(candidate_list, list):
        return patch, replace_paths, changed_paths
    if len(active_list) != len(candidate_list):
        raise RuntimeError("candidate agent list shape changed outside Skill policy")

    modified = copy.deepcopy(active_list)
    list_changed = False
    for index, (active_item, candidate_item) in enumerate(zip(active_list, candidate_list)):
        if not isinstance(active_item, dict) or not isinstance(candidate_item, dict):
            raise RuntimeError("candidate agent list contains an invalid entry")
        if active_item.get("id") != candidate_item.get("id"):
            raise RuntimeError("candidate agent identity changed outside Skill policy")
        changed, value = _changed_value(active_item, candidate_item, "skills")
        if not changed:
            continue
        if value is None:
            modified[index].pop("skills", None)
        else:
            modified[index]["skills"] = value
        changed_paths.append(f"agents.list[{index}].skills")
        list_changed = True
    if list_changed:
        patch.setdefault("agents", {})["list"] = modified
        replace_paths.append("agents.list")
    return patch, replace_paths, changed_paths


def build_policy_validation_patch(
    context: RuntimeContext,
    candidate_path: Path,
) -> tuple[Path, tuple[str, ...], dict[str, Any]]:
    active = load_json(context.openclaw_config)
    candidate = load_json(candidate_path)
    active_tools = active.get("tools")
    candidate_tools = candidate.get("tools")
    if not isinstance(active_tools, dict) or not isinstance(candidate_tools, dict):
        raise RuntimeError("OpenClaw tools policy is unavailable for dry-run validation")

    patch: dict[str, Any] = {}
    changed_paths: list[str] = []
    tools_patch: dict[str, Any] = {}
    for key in _TOOL_POLICY_KEYS:
        changed, value = _changed_value(active_tools, candidate_tools, key)
        if changed:
            tools_patch[key] = value
            changed_paths.append(f"tools.{key}")
    if tools_patch:
        patch["tools"] = tools_patch

    agent_patch, replace_paths, agent_paths = _agent_skill_patch(active, candidate)
    for key, value in agent_patch.items():
        patch[key] = value
    changed_paths.extend(agent_paths)
    if not patch:
        raise RuntimeError("candidate contains no policy delta to validate")

    patch_path = candidate_path.with_name("candidate-policy.patch.json")
    patch_path.write_text(
        json.dumps(patch, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(patch_path, 0o600)
    evidence = {
        "changed_paths": changed_paths,
        "replace_paths": replace_paths,
        "patch_roots": sorted(patch),
        "private_temporary_location": True,
        "patch_content_recorded": False,
        "secret_values_recorded": False,
    }
    return patch_path, tuple(replace_paths), evidence
