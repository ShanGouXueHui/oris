from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import RuntimeContext
from .process import run
from .tool_authority import WRITE_CAPABLE_CORE_TOOLS


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
        raise RuntimeError("tools.effective payload is unavailable")
    groups = payload.get("groups")
    if not isinstance(groups, list):
        raise RuntimeError("tools.effective groups are unavailable")

    approved = set(approved_tools)
    approved_seen: dict[str, dict[str, Any]] = {}
    total_count = 0
    plugin_count = 0
    write_tools_present = False
    for group in groups:
        if not isinstance(group, dict):
            raise RuntimeError("tools.effective group is invalid")
        tools = group.get("tools")
        if not isinstance(tools, list):
            raise RuntimeError("tools.effective group tools are invalid")
        for tool in tools:
            if not isinstance(tool, dict) or not isinstance(tool.get("id"), str):
                raise RuntimeError("tools.effective tool entry is invalid")
            name = tool["id"]
            total_count += 1
            source = tool.get("source")
            owner = tool.get("pluginId")
            if source == "plugin":
                plugin_count += 1
            if name in WRITE_CAPABLE_CORE_TOOLS:
                write_tools_present = True
            if name in approved:
                approved_seen[name] = {
                    "source": source if isinstance(source, str) else "",
                    "plugin_owned": source == "plugin" and owner == plugin_id,
                }

    present = sorted(approved_seen)
    missing = sorted(approved - set(present))
    wrong_owner = sorted(
        name
        for name, metadata in approved_seen.items()
        if metadata.get("plugin_owned") is not True
    )
    return {
        "status": "PASS" if not missing and not wrong_owner else "FAIL",
        "profile": payload.get("profile") if isinstance(payload.get("profile"), str) else "",
        "group_count": len(groups),
        "total_tool_count": total_count,
        "plugin_tool_count": plugin_count,
        "approved_tool_count": len(approved),
        "approved_tools_present": present,
        "missing_approved_tools": missing,
        "wrong_owner_approved_tools": wrong_owner,
        "all_approved_tools_present": not missing,
        "all_approved_tools_plugin_owned": not wrong_owner,
        "write_capable_core_tools_present": write_tools_present,
        "raw_output_recorded": False,
        "non_approved_tool_names_recorded": False,
        "tool_descriptions_recorded": False,
        "session_key_recorded": False,
        "secret_values_recorded": False,
    }


def probe_effective_tool_surface(
    context: RuntimeContext,
    session_key: str,
    agent_id: str,
) -> dict[str, Any]:
    params = json.dumps(
        {"sessionKey": session_key, "agentId": agent_id},
        separators=(",", ":"),
    )
    result = run(
        [
            "openclaw",
            "gateway",
            "call",
            "tools.effective",
            "--params",
            params,
            "--json",
            "--timeout",
            "30000",
        ],
        timeout=45,
    )
    combined = (result.stdout + "\n" + result.stderr).encode(
        "utf-8",
        errors="replace",
    )
    evidence: dict[str, Any] = {
        "command_returncode": result.returncode,
        "stdout_bytes": len(result.stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(result.stderr.encode("utf-8", errors="replace")),
        "output_sha256": hashlib.sha256(combined).hexdigest(),
        "rpc_method": "tools.effective",
        "raw_output_recorded": False,
        "session_key_recorded": False,
        "secret_values_recorded": False,
    }
    if result.returncode != 0:
        evidence.update(
            {
                "status": "FAIL",
                "reason_code": "tools_effective_rpc_failed",
            }
        )
        return evidence
    try:
        decoded = json.loads(result.stdout)
        summary = summarize_effective_tool_payload(
            decoded,
            context.approved_tools,
            context.plugin_id,
        )
    except (json.JSONDecodeError, RuntimeError):
        evidence.update(
            {
                "status": "FAIL",
                "reason_code": "tools_effective_payload_invalid",
            }
        )
        return evidence
    evidence.update(summary)
    evidence["reason_code"] = (
        None
        if summary["status"] == "PASS"
        else "approved_tools_absent_from_effective_surface"
    )
    return evidence
