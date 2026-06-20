from __future__ import annotations

from typing import Any

from .effective_tool_surface import probe_effective_tool_surface
from .models import RuntimeContext


_SAFE_SCALAR_FIELDS = (
    "command_returncode",
    "stdout_bytes",
    "stderr_bytes",
    "rpc_method",
    "profile",
    "group_count",
    "total_tool_count",
    "plugin_tool_count",
    "approved_tool_count",
)


def _safe_scalar_fields(value: dict[str, Any]) -> dict[str, Any]:
    return {
        field: value[field]
        for field in _SAFE_SCALAR_FIELDS
        if isinstance(value.get(field), (str, int))
        and not isinstance(value.get(field), bool)
    }


def sanitize_effective_tool_surface(
    value: dict[str, Any],
    approved_tools: tuple[str, ...],
) -> dict[str, Any]:
    approved = set(approved_tools)
    present = sorted(
        name
        for name in value.get("approved_tools_present", [])
        if isinstance(name, str) and name in approved
    )
    wrong_owner = sorted(
        name
        for name in value.get("wrong_owner_approved_tools", [])
        if isinstance(name, str) and name in approved
    )
    missing = sorted(approved - set(present))
    status = "PASS" if not missing and not wrong_owner else "FAIL"
    reason = value.get("reason_code")
    if not isinstance(reason, str) or not reason:
        if missing:
            reason = "approved_tools_absent_from_effective_surface"
        elif wrong_owner:
            reason = "approved_tools_not_plugin_owned"
        else:
            reason = None

    result: dict[str, Any] = {
        **_safe_scalar_fields(value),
        "status": status if value.get("status") != "FAIL" or present else "FAIL",
        "reason_code": reason,
        "approved_tools_present": present,
        "approved_tool_ownership": {
            name: name not in set(wrong_owner) for name in present
        },
        "missing_approved_tools": missing,
        "wrong_owner_approved_tools": wrong_owner,
        "all_approved_tools_present": not missing,
        "all_approved_tools_plugin_owned": not wrong_owner,
        "raw_output_recorded": False,
        "non_approved_tool_names_recorded": False,
        "tool_descriptions_recorded": False,
        "session_key_recorded": False,
        "provider_or_model_recorded": False,
        "sensitive_values_recorded": False,
    }
    if value.get("status") == "FAIL" and not present:
        result["status"] = "FAIL"
    return result


def probe_approved_effective_tool_surface(
    context: RuntimeContext,
    session_key: str,
    agent_id: str,
) -> dict[str, Any]:
    raw = probe_effective_tool_surface(context, session_key, agent_id)
    return sanitize_effective_tool_surface(raw, context.approved_tools)
