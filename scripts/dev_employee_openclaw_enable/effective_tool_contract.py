from __future__ import annotations

from typing import Any


def _payload(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("groups"), list):
        return value
    for key in ("payload", "result", "data"):
        child = value.get(key)
        if isinstance(child, dict) and isinstance(child.get("groups"), list):
            return child
    return None


def summarize_effective_tool_payload(
    value: Any,
    approved_tools: tuple[str, ...],
    plugin_id: str,
) -> dict[str, Any]:
    payload = _payload(value)
    if payload is None:
        raise RuntimeError("effective-tool payload is unavailable")
    groups = payload.get("groups")
    if not isinstance(groups, list):
        raise RuntimeError("effective-tool groups are unavailable")

    approved = set(approved_tools)
    approved_seen: dict[str, bool] = {}
    total_count = 0
    plugin_count = 0
    for group in groups:
        if not isinstance(group, dict):
            raise RuntimeError("effective-tool group is invalid")
        tools = group.get("tools")
        if not isinstance(tools, list):
            raise RuntimeError("effective-tool group tools are invalid")
        for tool in tools:
            if not isinstance(tool, dict) or not isinstance(tool.get("id"), str):
                raise RuntimeError("effective-tool entry is invalid")
            name = tool["id"]
            total_count += 1
            source = tool.get("source")
            owner = tool.get("pluginId")
            if source == "plugin":
                plugin_count += 1
            if name in approved:
                approved_seen[name] = source == "plugin" and owner == plugin_id

    present = sorted(approved_seen)
    missing = sorted(approved - set(present))
    wrong_owner = sorted(
        name for name, plugin_owned in approved_seen.items() if not plugin_owned
    )
    return {
        "status": "PASS" if not missing and not wrong_owner else "FAIL",
        "profile": payload.get("profile") if isinstance(payload.get("profile"), str) else "",
        "group_count": len(groups),
        "total_tool_count": total_count,
        "plugin_tool_count": plugin_count,
        "approved_tool_count": len(approved),
        "approved_tools_present": present,
        "approved_tool_ownership": dict(sorted(approved_seen.items())),
        "missing_approved_tools": missing,
        "wrong_owner_approved_tools": wrong_owner,
        "all_approved_tools_present": not missing,
        "all_approved_tools_plugin_owned": not wrong_owner,
        "raw_output_recorded": False,
        "non_approved_tool_names_recorded": False,
        "tool_descriptions_recorded": False,
        "session_key_recorded": False,
        "sensitive_values_recorded": False,
    }
