from __future__ import annotations

from typing import Any

from .agent_output import parse_json_value
from .models import RuntimeContext
from .process import run


def _skill_record(value: Any, skill_name: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        identity = value.get("name") or value.get("id") or value.get("slug")
        if identity == skill_name:
            return value
        for child in value.values():
            found = _skill_record(child, skill_name)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _skill_record(child, skill_name)
            if found is not None:
                return found
    return None


def _record_visible(record: dict[str, Any]) -> bool:
    for key in ("eligible", "ready", "enabled", "visible"):
        if record.get(key) is False:
            return False
    for key in ("disabled", "blocked", "missing", "ineligible"):
        if record.get(key) is True:
            return False
    status = record.get("status")
    if isinstance(status, str) and status.lower() in {
        "disabled",
        "blocked",
        "missing",
        "ineligible",
        "unavailable",
    }:
        return False
    return True


def verify_routing_skill_runtime(
    context: RuntimeContext,
    agent_id: str,
) -> dict[str, Any]:
    commands = (
        ["openclaw", "skills", "info", context.routing_skill_name, "--json", "--agent", agent_id],
        ["openclaw", "skills", "list", "--json", "--agent", agent_id],
        ["openclaw", "skills", "check", "--json", "--agent", agent_id],
        ["openclaw", "skills", "info", context.routing_skill_name, "--json"],
        ["openclaw", "skills", "list", "--json"],
        ["openclaw", "skills", "check", "--json"],
    )
    attempted = 0
    for command in commands:
        result = run(command, timeout=45)
        attempted += 1
        if result.returncode != 0:
            continue
        payload = parse_json_value(result.stdout)
        if payload is None:
            continue
        record = _skill_record(payload, context.routing_skill_name)
        if record is None:
            continue
        return {
            "visible": _record_visible(record),
            "inventory_command": " ".join(command[1:3]),
            "agent_id": agent_id,
            "attempted_commands": attempted,
            "skill_recorded": False,
            "secret_values_recorded": False,
        }
    return {
        "visible": False,
        "reason": "routing_skill_not_found_in_agent_inventory",
        "agent_id": agent_id,
        "attempted_commands": attempted,
        "skill_recorded": False,
        "secret_values_recorded": False,
    }
