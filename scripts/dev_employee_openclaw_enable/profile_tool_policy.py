from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .task_contract import require_unique_strings


@dataclass(frozen=True)
class ProfileToolPolicyChange:
    mode: str
    allow_mode: str
    also_allow_mode: str
    added_to_allow: tuple[str, ...]
    added_to_also_allow: tuple[str, ...]
    allow_existed_before: bool
    also_allow_existed_before: bool
    allow_before_count: int
    allow_after_count: int
    also_allow_before_count: int
    also_allow_after_count: int

    def evidence(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "allow_mode": self.allow_mode,
            "also_allow_mode": self.also_allow_mode,
            "allow_added_count": len(self.added_to_allow),
            "also_allow_added_count": len(self.added_to_also_allow),
            "allow_existed_before": self.allow_existed_before,
            "also_allow_existed_before": self.also_allow_existed_before,
            "allow_before_count": self.allow_before_count,
            "allow_after_count": self.allow_after_count,
            "also_allow_before_count": self.also_allow_before_count,
            "also_allow_after_count": self.also_allow_after_count,
            "secret_values_recorded": False,
        }


def _values(value: Any, label: str) -> list[str]:
    return list(require_unique_strings(value, label))


def _append_missing(existing: list[str], additions: tuple[str, ...]) -> tuple[list[str], tuple[str, ...]]:
    result = list(existing)
    added: list[str] = []
    seen = set(existing)
    for item in additions:
        if item not in seen:
            result.append(item)
            added.append(item)
            seen.add(item)
    return result, tuple(added)


def validate_tool_policy_shape(tools: dict[str, Any], required_profile: str) -> None:
    if tools.get("profile") != required_profile:
        raise RuntimeError("OpenClaw tool profile differs from the approved profile")
    _values(tools.get("deny"), "OpenClaw tools.deny")
    for key in ("allow", "alsoAllow"):
        if key in tools:
            _values(tools[key], f"OpenClaw tools.{key}")


def enable_profile_tools(
    tools: dict[str, Any],
    approved_tools: tuple[str, ...],
    profile_expansion: tuple[str, ...],
    required_profile: str,
) -> ProfileToolPolicyChange:
    validate_tool_policy_shape(tools, required_profile)
    approved = require_unique_strings(list(approved_tools), "approved tools")
    profile_tools = require_unique_strings(list(profile_expansion), "profile expansion")
    deny = _values(tools["deny"], "OpenClaw tools.deny")

    allow_existed = "allow" in tools
    old_allow = _values(tools["allow"], "OpenClaw tools.allow") if allow_existed else []
    additions = approved if allow_existed else (*profile_tools, *approved)
    new_allow, added_allow = _append_missing(old_allow, additions)
    tools["allow"] = new_allow
    allow_mode = "preserved-allow-plus-approved" if allow_existed else "materialized-profile-plus-approved"

    also_existed = "alsoAllow" in tools
    old_also = _values(tools["alsoAllow"], "OpenClaw tools.alsoAllow") if also_existed else []
    new_also, added_also = _append_missing(old_also, approved)
    tools["alsoAllow"] = new_also
    if not added_also:
        also_mode = "profile-also-allow-already-complete"
    elif also_existed:
        also_mode = "extended-profile-also-allow"
    else:
        also_mode = "created-profile-also-allow"

    tools["deny"] = [item for item in deny if item not in set(approved)]
    return ProfileToolPolicyChange(
        mode=f"{allow_mode}+{also_mode}",
        allow_mode=allow_mode,
        also_allow_mode=also_mode,
        added_to_allow=added_allow,
        added_to_also_allow=added_also,
        allow_existed_before=allow_existed,
        also_allow_existed_before=also_existed,
        allow_before_count=len(old_allow),
        allow_after_count=len(new_allow),
        also_allow_before_count=len(old_also),
        also_allow_after_count=len(new_also),
    )


def _strip(tools: dict[str, Any], key: str, added: tuple[str, ...], existed: bool) -> None:
    values = _values(tools.get(key), f"authorized tools.{key}")
    for item in added:
        if values.count(item) != 1:
            raise RuntimeError(f"authorized tools.{key} addition is missing or duplicated")
        values.remove(item)
    if existed:
        tools[key] = values
    elif values:
        raise RuntimeError(f"unexpected tools.{key} entries appeared")
    else:
        tools.pop(key, None)


def strip_authorized_tool_change(config: dict[str, Any], change: ProfileToolPolicyChange) -> dict[str, Any]:
    copied = copy.deepcopy(config)
    tools = copied.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy disappeared")
    tools.pop("deny", None)
    _strip(tools, "allow", change.added_to_allow, change.allow_existed_before)
    _strip(tools, "alsoAllow", change.added_to_also_allow, change.also_allow_existed_before)
    return copied


def approved_tools_are_profile_visible(
    tools: dict[str, Any], approved_tools: tuple[str, ...], required_profile: str
) -> bool:
    try:
        validate_tool_policy_shape(tools, required_profile)
        deny = set(_values(tools["deny"], "OpenClaw tools.deny"))
        allow = set(_values(tools.get("allow"), "OpenClaw tools.allow"))
        also = set(_values(tools.get("alsoAllow"), "OpenClaw tools.alsoAllow"))
    except RuntimeError:
        return False
    approved = set(approved_tools)
    return approved.isdisjoint(deny) and approved.issubset(allow) and approved.issubset(also)
