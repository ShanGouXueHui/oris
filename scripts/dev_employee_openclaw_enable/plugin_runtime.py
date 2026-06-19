from __future__ import annotations

import json
from typing import Any

from .models import RuntimeContext
from .process import run


def _collect_runtime_names(value: Any, tools: set[str], hooks: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            target = tools if lowered in {"tools", "registeredtools", "toolnames"} else None
            if lowered in {
                "hooks",
                "registeredhooks",
                "hooknames",
                "typedhooks",
                "customhooks",
            }:
                target = hooks
            if isinstance(child, list) and target is not None:
                for item in child:
                    if isinstance(item, str):
                        target.add(item)
                    elif isinstance(item, dict):
                        name = (
                            item.get("name")
                            or item.get("id")
                            or item.get("toolName")
                            or item.get("hookName")
                        )
                        if isinstance(name, str):
                            target.add(name)
            elif isinstance(child, dict) and target is not None:
                target.update(str(name) for name in child)
            _collect_runtime_names(child, tools, hooks)
    elif isinstance(value, list):
        for child in value:
            _collect_runtime_names(child, tools, hooks)


def verify_plugin_runtime(context: RuntimeContext) -> dict[str, Any]:
    listing = run(["openclaw", "plugins", "list", "--json"], timeout=30)
    runtime = run(
        ["openclaw", "plugins", "inspect", context.plugin_id, "--runtime", "--json"],
        timeout=30,
    )
    if listing.returncode != 0 or runtime.returncode != 0:
        return {"ok": False, "reason": "plugin_inventory_command_failed"}
    try:
        listed = json.loads(listing.stdout)
        inspected = json.loads(runtime.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "reason": "plugin_inventory_json_invalid"}

    plugin_found = False
    plugin_enabled = False
    plugin_version_ok = False
    plugin_errors = 0
    for item in listed.get("plugins", []) if isinstance(listed, dict) else []:
        if not isinstance(item, dict):
            continue
        identity = str(item.get("id") or item.get("name") or "")
        if identity != context.plugin_id:
            continue
        plugin_found = True
        plugin_enabled = item.get("enabled") is True
        plugin_version_ok = str(item.get("version") or "") == context.plugin_version
        if item.get("status") == "error" or item.get("error"):
            plugin_errors += 1

    tools: set[str] = set()
    hooks: set[str] = set()
    _collect_runtime_names(inspected, tools, hooks)
    write_terms = (
        "submit",
        "cancel",
        "retry",
        "create",
        "enqueue",
        "write",
        "delete",
        "update",
    )
    write_tools = {
        name for name in tools if any(term in name.lower() for term in write_terms)
    }
    ok = bool(
        plugin_found
        and plugin_enabled
        and plugin_version_ok
        and plugin_errors == 0
        and tools == set(context.approved_tools)
        and hooks == set(context.required_hooks)
        and not write_tools
    )
    return {
        "ok": ok,
        "plugin_found": plugin_found,
        "plugin_enabled": plugin_enabled,
        "plugin_version_ok": plugin_version_ok,
        "plugin_error_count": plugin_errors,
        "tools": sorted(tools),
        "hooks": sorted(hooks),
        "write_tools": sorted(write_tools),
    }
