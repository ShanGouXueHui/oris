from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import RuntimeContext
from .state import load_json


_GROUP_SELECTOR = re.compile(r"group:[a-z0-9][a-z0-9_-]*", re.IGNORECASE)


def candidate_policy_compatibility(
    context: RuntimeContext,
    candidate_path: Path,
) -> dict[str, Any]:
    candidate = load_json(candidate_path)
    tools = candidate.get("tools")
    if not isinstance(tools, dict):
        return {"status": "FAIL", "reason_code": "candidate_tools_policy_missing"}
    allow = tools.get("allow")
    also_allow = tools.get("alsoAllow")
    deny = tools.get("deny")
    lists = (allow, also_allow, deny)
    if not all(
        isinstance(value, list) and all(isinstance(item, str) for item in value)
        for value in lists
    ):
        return {"status": "FAIL", "reason_code": "candidate_tool_lists_invalid"}

    approved = set(context.approved_tools)
    profile_expansion = set(context.profile_expansion)
    group_selectors = [
        item for item in context.profile_expansion if item.lower().startswith("group")
    ]
    checks = {
        "profile_matches": tools.get("profile") == context.required_profile,
        "allow_unique": len(allow) == len(set(allow)),
        "also_allow_unique": len(also_allow) == len(set(also_allow)),
        "deny_unique": len(deny) == len(set(deny)),
        "profile_expansion_materialized": profile_expansion.issubset(set(allow)),
        "approved_materialized": approved.issubset(set(allow)),
        "approved_profile_authorized": approved.issubset(set(also_allow)),
        "approved_removed_from_deny": approved.isdisjoint(set(deny)),
        "group_selectors_well_formed": all(
            _GROUP_SELECTOR.fullmatch(item) is not None for item in group_selectors
        ),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "allow_count": len(allow),
        "also_allow_count": len(also_allow),
        "deny_count": len(deny),
        "group_selector_count": len(group_selectors),
        "approved_tool_count": len(approved),
        "candidate_config_recorded": False,
    }
