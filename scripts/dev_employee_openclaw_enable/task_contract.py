from __future__ import annotations

from typing import Any


_REQUIRED_ARCHITECTURE_KEYS = (
    "primary_public_entry",
    "openclaw_local_gateway",
)
_REQUIRED_PLATFORM_KEYS = (
    "openclaw_version",
    "openclaw_gateway_port",
    "enqueue_status_port",
    "intake_port",
    "product_baseline_commit",
)
_REQUIRED_PLUGIN_KEYS = (
    "plugin_id",
    "version",
    "runtime_tools",
    "runtime_hooks",
    "private_marker",
)


def _required_mapping(task: dict[str, Any], key: str) -> dict[str, Any]:
    value = task.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"current_task_contract_invalid:{key}")
    return value


def _require_keys(scope: str, value: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in value:
            raise RuntimeError(f"current_task_contract_missing:{scope}.{key}")
        item = value[key]
        if item is None or item == "":
            raise RuntimeError(f"current_task_contract_empty:{scope}.{key}")


def validate_current_task(
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    task_id = task.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise RuntimeError("current_task_contract_missing:task_id")

    architecture = _required_mapping(task, "architecture_decision")
    platform = _required_mapping(task, "platform_state")
    plugin = _required_mapping(task, "installed_plugin_state")
    _require_keys("architecture_decision", architecture, _REQUIRED_ARCHITECTURE_KEYS)
    _require_keys("platform_state", platform, _REQUIRED_PLATFORM_KEYS)
    _require_keys("installed_plugin_state", plugin, _REQUIRED_PLUGIN_KEYS)

    tools = plugin.get("runtime_tools")
    hooks = plugin.get("runtime_hooks")
    if not isinstance(tools, list) or not all(isinstance(item, str) for item in tools):
        raise RuntimeError("current_task_contract_invalid:installed_plugin_state.runtime_tools")
    if not isinstance(hooks, list) or not all(isinstance(item, str) for item in hooks):
        raise RuntimeError("current_task_contract_invalid:installed_plugin_state.runtime_hooks")
    return architecture, platform, plugin
