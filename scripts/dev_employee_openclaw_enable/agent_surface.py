from __future__ import annotations

from typing import Any


def merge_effective_surfaces(
    surfaces: list[dict[str, Any]],
    approved_tools: set[str],
) -> dict[str, Any]:
    checked = [item for item in surfaces if item.get("status") != "NOT_CHECKED"]
    present = {
        name
        for item in checked
        for name in item.get("approved_tools_present", [])
        if isinstance(name, str)
    }
    missing = approved_tools - present
    return {
        "status": "NOT_CHECKED" if not checked else "PASS" if not missing else "FAIL",
        "reports_observed": sum(int(item.get("report_count") or 0) for item in surfaces),
        "max_total_tool_count": max(
            [int(item.get("total_tool_count") or 0) for item in surfaces] or [0]
        ),
        "approved_tools_present": sorted(present),
        "missing_approved_tools": sorted(missing),
        "routing_skill_present": any(
            item.get("routing_skill_present") is True for item in checked
        ),
        "other_tool_names_recorded": False,
        "system_prompt_recorded": False,
        "conversation_content_recorded": False,
    }
