from __future__ import annotations

import hashlib
import json
import time
from urllib import error as urllib_error
from urllib import request as urllib_request
from typing import Any

from .models import RuntimeContext
from .state import load_json


def _gateway_credential(context: RuntimeContext) -> str:
    config = load_json(context.openclaw_config)
    auth = config.get("gateway", {}).get("auth", {})
    if auth.get("mode") != "token":
        raise RuntimeError("Gateway auth mode is not token")
    value = auth.get("token")
    if not isinstance(value, str) or not value:
        raise RuntimeError("Gateway credential is unavailable")
    return value


def _join_url(base: str, route: str) -> str:
    return base.rstrip("/") + "/" + route.lstrip("/")


def _http_get(url: str, timeout: int = 10) -> tuple[int, bytes]:
    request = urllib_request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(2_000_000)
    except urllib_error.HTTPError as exc:
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
    restricted_ok = all(
        status in {401, 403, 404} for status in restricted_statuses.values()
    )
    return {
        "ok": bool(
            direct_status == 200
            and public_status == 200
            and direct_hash == public_hash
            and restricted_ok
        ),
        "direct_status": direct_status,
        "public_status": public_status,
        "restricted_statuses": restricted_statuses,
        "root_bodies_match": direct_hash == public_hash,
    }


def invoke_tool(
    context: RuntimeContext,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    body = json.dumps(
        {
            "tool": tool_name,
            "args": arguments,
            "sessionKey": context.direct_probe_session_key,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib_request.Request(
        _join_url(context.gateway_url, "/tools/invoke"),
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + _gateway_credential(context),
            "Content-Type": "application/json",
        },
    )
    started = time.perf_counter()
    status = 0
    payload: dict[str, Any] = {}
    try:
        with urllib_request.urlopen(request, timeout=20) as response:
            status = response.status
            decoded = json.loads(response.read(1_000_000))
            if isinstance(decoded, dict):
                payload = decoded
    except urllib_error.HTTPError as exc:
        status = exc.code
    except Exception:
        status = 0
    return {
        "status": status,
        "ok": status == 200 and payload.get("ok") is True,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
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


def direct_readonly_probe(
    context: RuntimeContext,
    baseline_tool: str,
) -> dict[str, Any]:
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
        if invoke_tool(context, candidate, {})["ok"]:
            return candidate
    raise RuntimeError("no approved safe built-in baseline tool is accessible")
