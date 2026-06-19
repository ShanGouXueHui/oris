from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from typing import Any

from .models import RuntimeContext
from .process import run
from .state import load_json


def _gateway_token(context: RuntimeContext) -> str:
    config = load_json(context.openclaw_config)
    auth = config.get("gateway", {}).get("auth", {})
    if auth.get("mode") != "token":
        raise RuntimeError("Gateway auth mode is not token")
    token = auth.get("token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Gateway token is unavailable")
    return token


def _join_url(base: str, route: str) -> str:
    return base.rstrip("/") + "/" + route.lstrip("/")


def restart_gateway(context: RuntimeContext, timeout_seconds: int = 45) -> None:
    restarted = run(["systemctl", "--user", "restart", context.gateway_service])
    if restarted.returncode != 0:
        raise RuntimeError("existing OpenClaw Gateway restart failed")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        active = run(["systemctl", "--user", "is-active", context.gateway_service])
        if active.returncode == 0 and active.stdout.strip() == "active":
            status, _ = _http_get(_join_url(context.gateway_url, context.public_root_route), timeout=5)
            if status == 200:
                return
        time.sleep(1)
    raise RuntimeError("existing OpenClaw Gateway did not become healthy")


def gateway_pid(context: RuntimeContext) -> str:
    result = run(
        ["systemctl", "--user", "show", context.gateway_service, "-p", "MainPID", "--value"]
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _http_get(url: str, timeout: int = 10) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(2_000_000)
    except Exception:
        return 0, b""


def verify_public_routes(context: RuntimeContext) -> dict[str, Any]:
    direct_url = _join_url(context.gateway_url, context.public_root_route)
    public_url = _join_url(context.public_url, context.public_root_route)
    direct_status, direct_body = _http_get(direct_url)
    public_status, public_body = _http_get(public_url)
    restricted_statuses: dict[str, int] = {}
    for route in context.restricted_routes:
        status, _ = _http_get(_join_url(context.public_url, route))
        restricted_statuses[route] = status
    direct_hash = hashlib.sha256(direct_body).hexdigest()
    public_hash = hashlib.sha256(public_body).hexdigest()
    restricted_ok = all(status in {401, 403, 404} for status in restricted_statuses.values())
    return {
        "ok": direct_status == 200 and public_status == 200 and direct_hash == public_hash and restricted_ok,
        "direct_status": direct_status,
        "public_status": public_status,
        "restricted_statuses": restricted_statuses,
        "root_bodies_match": direct_hash == public_hash,
    }


def invoke_tool(context: RuntimeContext, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(
        {
            "tool": tool_name,
            "args": arguments,
            "sessionKey": context.direct_probe_session_key,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        _join_url(context.gateway_url, "/tools/invoke"),
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + _gateway_token(context),
            "Content-Type": "application/json",
        },
    )
    started = time.perf_counter()
    status = 0
    payload: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            decoded = json.loads(response.read(1_000_000))
            if isinstance(decoded, dict):
                payload = decoded
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception:
        status = 0
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "status": status,
        "ok": status == 200 and payload.get("ok") is True,
        "duration_ms": duration_ms,
        "payload": payload,
    }


def _oris_contract_ok(context: RuntimeContext, result: dict[str, Any]) -> bool:
    payload = result.get("payload")
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    tool_result = payload.get("result")
    if not isinstance(tool_result, dict):
        return False
    details = tool_result.get("details")
    content = tool_result.get("content")
    if not isinstance(details, dict) or not isinstance(content, list) or not content:
        return False
    if not (
        details.get("source") == context.plugin_id
        and details.get("readOnly") is True
        and details.get("sanitized") is True
    ):
        return False
    first = content[0]
    if not isinstance(first, dict) or not isinstance(first.get("text"), str):
        return False
    try:
        json.loads(first["text"])
    except json.JSONDecodeError:
        return False
    return True


def direct_readonly_probe(context: RuntimeContext, baseline_tool: str) -> dict[str, Any]:
    calls = [
        (baseline_tool, {}),
        (context.approved_tools[0], {}),
        (context.approved_tools[1], {"task_id": context.task_id}),
        (context.approved_tools[2], {}),
    ]
    rows: list[dict[str, Any]] = []
    for tool_name, arguments in calls:
        result = invoke_tool(context, tool_name, arguments)
        contract_ok = (
            result["ok"]
            if tool_name == baseline_tool
            else _oris_contract_ok(context, result)
        )
        rows.append(
            {
                "tool": tool_name,
                "status": result["status"],
                "duration_ms": result["duration_ms"],
                "contract_ok": bool(contract_ok),
            }
        )
    return {
        "ok": all(row["contract_ok"] for row in rows),
        "calls": rows,
        "tool_results_recorded": False,
        "secret_values_recorded": False,
    }


def select_safe_baseline_tool(context: RuntimeContext) -> str:
    for candidate in context.safe_probe_candidates:
        result = invoke_tool(context, candidate, {})
        if result["ok"]:
            return candidate
    raise RuntimeError("no approved safe built-in baseline tool is accessible")


def _collect_runtime_names(value: Any, tools: set[str], hooks: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            target = tools if lowered in {"tools", "registeredtools", "toolnames"} else None
            if lowered in {"hooks", "registeredhooks", "hooknames", "typedhooks", "customhooks"}:
                target = hooks
            if target is not None:
                if isinstance(child, list):
                    for item in child:
                        if isinstance(item, str):
                            target.add(item)
                        elif isinstance(item, dict):
                            name = item.get("name") or item.get("id") or item.get("toolName") or item.get("hookName")
                            if isinstance(name, str):
                                target.add(name)
                elif isinstance(child, dict):
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
    write_tools = {
        name
        for name in tools
        if any(
            term in name.lower()
            for term in (
                "submit",
                "cancel",
                "retry",
                "create",
                "enqueue",
                "write",
                "delete",
                "update",
            )
        )
    }
    ok = (
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
