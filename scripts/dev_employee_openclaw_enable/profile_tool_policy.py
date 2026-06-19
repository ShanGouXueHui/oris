from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


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


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeError(f"{label} must be a string list")
    if len(value) != len(set(value)):
        raise RuntimeError(f"{label} contains duplicate entries")
    return value


def _unique(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if not all(isinstance(item, str) and item for item in values):
        raise RuntimeError(f"{label} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise RuntimeError(f"{label} contains duplicate entries")
    return values


def _append_missing(existing: list[str], additions: tuple[str, ...]) -> tuple[list[str], tuple[str, ...]]:
    seen = set(existing)
    added: list[str] = []
    result = list(existing)
    for item in additions:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
        added.append(item)
    return result, tuple(added)


def validate_tool_policy_shape(
    tools: dict[str, Any],
    required_profile: str,
) -> None:
    if tools.get("profile") != required_profile:
        raise RuntimeError("OpenClaw tool profile differs from the approved profile")
    _string_list(tools.get("deny"), "OpenClaw tools.deny")
    for key in ("allow", "alsoAllow"):
        if key in tools:
            _string_list(tools[key], f"OpenClaw tools.{key}")


def enable_profile_tools(
    tools: dict[str, Any],
    approved_tools: tuple[str, ...],
    profile_expansion: tuple[str, ...],
    required_profile: str,
) -> ProfileToolPolicyChange:
    validate_tool_policy_shape(tools, required_profile)
    approved = _unique(approved_tools, "approved tools")
    profile_tools = _unique(profile_expansion, "profile expansion")
    approved_set = set(approved)
    deny = _string_list(tools["deny"], "OpenClaw tools.deny")

    allow_existed = "allow" in tools
    existing_allow = (
        _string_list(tools["allow"], "OpenClaw tools.allow")
        if allow_existed
        else []
    )
    allow_additions = approved if allow_existed else (*profile_tools, *approved)
    next_allow, added_to_allow = _append_missing(existing_allow, allow_additions)
    tools["allow"] = next_allow
    allow_mode = (
        "preserved-allow-plus-approved"
        if allow_existed
        else "materialized-profile-plus-approved"
    )

    also_allow_existed = "alsoAllow" in tools
    existing_also_allow = (
        _string_list(tools["alsoAllow"], "OpenClaw tools.alsoAllow")
        if also_allow_existed
        else []
    )
    next_also_allow, added_to_also_allow = _append_missing(
        existing_also_allow,
        approved,
    )
    tools["alsoAllow"] = next_also_allow
    if not added_to_also_allow:
        also_allow_mode = "profile-also-allow-already-complete"
    elif also_allow_existed:
        also_allow_mode = "extended-profile-also-allow"
    else:
        also_allow_mode = "created-profile-also-allow"

    tools["deny"] = [item for item in deny if item not in approved_set]
    return ProfileToolPolicyChange(
        mode=f"{allow_mode}+{also_allow_mode}",
        allow_mode=allow_mode,
        also_allow_mode=also_allow_mode,
        added_to_allow=added_to_allow,
        added_to_also_allow=added_to_also_allow,
        allow_existed_before=allow_existed,
        also_allow_existed_before=also_allow_existed,
        allow_before_count=len(existing_allow),
        allow_after_count=len(next_allow),
        also_allow_before_count=len(existing_also_allow),
        also_allow_after_count=len(next_also_allow),
    )


def _strip_added_list(
    tools: dict[str, Any],
    key: str,
    added: tuple[str, ...],
    existed_before: bool,
) -> None:
    values = _string_list(tools.get(key), f"authorized tools.{key}")
    for item in added:
        if values.count(item) != 1:
            raise RuntimeError(f"authorized tools.{key} addition is missing or duplicated")
        values.remove(item)
    if existed_before:
        tools[key] = values
        return
    if values:
        raise RuntimeError(f"unexpected tools.{key} entries appeared")
    tools.pop(key, None)


def strip_authorized_tool_change(
    config: dict[str, Any],
    change: ProfileToolPolicyChange,
) -> dict[str, Any]:
    copied = copy.deepcopy(config)
    tools = copied.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy disappeared")
    tools.pop("deny", None)
    _strip_added_list(
        tools,
        "allow",
        change.added_to_allow,
        change.allow_existed_before,
    )
    _strip_added_list(
        tools,
        "alsoAllow",
        change.added_to_also_allow,
        change.also_allow_existed_before,
    )
    return copied


def approved_tools_are_profile_visible(
    tools: dict[str, Any],
    approved_tools: tuple[str, ...],
    required_profile: str,
) -> bool:
    try:
        validate_tool_policy_shape(tools, required_profile)
    except RuntimeError:
        return False
    deny = set(_string_list(tools["deny"], "OpenClaw tools.deny"))
    allow = set(_string_list(tools.get("allow"), "OpenClaw tools.allow"))
    also_allow = set(
        _string_list(tools.get("alsoAllow"), "OpenClaw tools.alsoAllow")
    )
    approved = set(approved_tools)
    return (
        approved.isdisjoint(deny)
        and approved.issubset(allow)
        and approved.issubset(also_allow)
    )
