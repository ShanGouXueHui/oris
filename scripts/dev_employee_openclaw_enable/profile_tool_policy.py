from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfileToolPolicyChange:
    mode: str
    added_to_also_allow: tuple[str, ...]
    also_allow_existed_before: bool
    before_count: int
    after_count: int

    def evidence(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "added_count": len(self.added_to_also_allow),
            "also_allow_existed_before": self.also_allow_existed_before,
            "before_count": self.before_count,
            "after_count": self.after_count,
            "secret_values_recorded": False,
        }


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeError(f"{label} must be a string list")
    if len(value) != len(set(value)):
        raise RuntimeError(f"{label} contains duplicate entries")
    return value


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
    required_profile: str,
) -> ProfileToolPolicyChange:
    validate_tool_policy_shape(tools, required_profile)
    approved = list(approved_tools)
    approved_set = set(approved)
    deny = _string_list(tools["deny"], "OpenClaw tools.deny")
    existed = "alsoAllow" in tools
    existing = (
        _string_list(tools["alsoAllow"], "OpenClaw tools.alsoAllow")
        if existed
        else []
    )
    added = tuple(item for item in approved if item not in set(existing))
    tools["alsoAllow"] = [*existing, *added]
    tools["deny"] = [item for item in deny if item not in approved_set]
    if not added:
        mode = "profile-also-allow-already-complete"
    elif existed:
        mode = "extended-profile-also-allow"
    else:
        mode = "created-profile-also-allow"
    return ProfileToolPolicyChange(
        mode=mode,
        added_to_also_allow=added,
        also_allow_existed_before=existed,
        before_count=len(existing),
        after_count=len(tools["alsoAllow"]),
    )


def strip_authorized_tool_change(
    config: dict[str, Any],
    change: ProfileToolPolicyChange,
) -> dict[str, Any]:
    copied = copy.deepcopy(config)
    tools = copied.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy disappeared")
    tools.pop("deny", None)
    values = _string_list(tools.get("alsoAllow"), "authorized tools.alsoAllow")
    for item in change.added_to_also_allow:
        if values.count(item) != 1:
            raise RuntimeError("authorized tools.alsoAllow addition is missing or duplicated")
        values.remove(item)
    if not change.also_allow_existed_before:
        if values:
            raise RuntimeError("unexpected tools.alsoAllow entries appeared")
        tools.pop("alsoAllow", None)
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
    also_allow = set(
        _string_list(tools.get("alsoAllow"), "OpenClaw tools.alsoAllow")
    )
    approved = set(approved_tools)
    return approved.isdisjoint(deny) and approved.issubset(also_allow)
