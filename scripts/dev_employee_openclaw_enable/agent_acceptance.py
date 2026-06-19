from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from .models import RuntimeContext
from .process import run
from .telemetry import inspect_telemetry


def _long_flag_from_help(help_text: str, candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in help_text:
            return candidate
    return None


def _message_flag_from_help(help_text: str) -> str | None:
    if "--message" in help_text:
        return "--message"
    if re.search(r"(^|[\s,])-m(?:[\s,]|$)", help_text):
        return "-m"
    return None


def _parse_json_output(value: str) -> dict[str, Any] | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _find_transport_metadata(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        meta = value.get("meta")
        if isinstance(meta, dict):
            transport = meta.get("transport")
            fallback_from = meta.get("fallbackFrom")
            if isinstance(transport, str) or isinstance(fallback_from, str):
                return (
                    transport if isinstance(transport, str) else None,
                    fallback_from if isinstance(fallback_from, str) else None,
                )
        for child in value.values():
            transport, fallback_from = _find_transport_metadata(child)
            if transport is not None or fallback_from is not None:
                return transport, fallback_from
    elif isinstance(value, list):
        for child in value:
            transport, fallback_from = _find_transport_metadata(child)
            if transport is not None or fallback_from is not None:
                return transport, fallback_from
    return None, None


def discover_agent_cli() -> dict[str, Any]:
    result = run(["openclaw", "agent", "--help"], timeout=30)
    help_text = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        raise RuntimeError("openclaw agent help failed")
    session_flag = _long_flag_from_help(
        help_text,
        ("--session-key", "--session-id", "--session"),
    )
    message_flag = _message_flag_from_help(help_text)
    json_flag = _long_flag_from_help(help_text, ("--json",))
    if session_flag is None or message_flag is None or json_flag is None:
        raise RuntimeError("OpenClaw agent CLI lacks required session, message, or JSON flags")
    return {
        "session_flag": session_flag,
        "message_flag": message_flag,
        "json_flag": json_flag,
        "local_flag_available": "--local" in help_text,
    }


def _failed_result(reason: str, cli: dict[str, Any]) -> dict[str, Any]:
    return {
        "accepted": False,
        "reason": reason,
        "cli": cli,
        "turns": [],
        "gateway_transport_mode": "unverified",
        "local_flag_used": False,
        "session_key_recorded": False,
        "conversation_content_recorded": False,
        "secret_values_recorded": False,
    }


def run_automatic_acceptance(context: RuntimeContext, stamp: str) -> dict[str, Any]:
    cli = discover_agent_cli()
    session_key = f"{context.session_prefix}-{stamp.lower()}"
    started_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    turns: list[dict[str, Any]] = []
    for turn in context.acceptance_turns:
        message = str(turn["message_template"]).format(task_id=context.task_id)
        command = [
            "openclaw",
            "agent",
            str(cli["session_flag"]),
            session_key,
            str(cli["message_flag"]),
            message,
            str(cli["json_flag"]),
        ]
        started = time.perf_counter()
        result = run(command, timeout=context.turn_timeout_seconds)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        payload = _parse_json_output(result.stdout)
        transport, fallback_from = _find_transport_metadata(payload)
        embedded_fallback = transport == "embedded" or fallback_from == "gateway"
        gateway_transport_ok = not embedded_fallback
        turns.append(
            {
                "intent": str(turn["intent"]),
                "expected_tool": str(turn["expected_tool"]),
                "returncode": result.returncode,
                "duration_ms": duration_ms,
                "output_present": bool(result.stdout.strip()),
                "structured_output_valid": payload is not None,
                "gateway_transport_ok": gateway_transport_ok,
                "reported_transport": transport or "gateway_default_unmarked",
                "fallback_from_gateway": fallback_from == "gateway",
                "stdout_bytes": len(result.stdout.encode("utf-8")),
                "stderr_bytes": len(result.stderr.encode("utf-8")),
            }
        )
        if result.returncode != 0 or payload is None or (
            context.require_gateway_transport and not gateway_transport_ok
        ):
            failed = _failed_result(
                "embedded_fallback_rejected" if embedded_fallback else "native_agent_turn_failed",
                cli,
            )
            failed["turns"] = turns
            return failed

    deadline = time.monotonic() + context.telemetry_wait_seconds
    telemetry: dict[str, Any] = {}
    while time.monotonic() < deadline:
        telemetry = inspect_telemetry(context, started_at, session_key)
        if telemetry.get("accepted") is True:
            break
        time.sleep(3)
    session_ok = bool(telemetry.get("persisted_session"))
    if not context.require_persisted_native_session:
        session_ok = True
    transport_ok = all(turn.get("gateway_transport_ok") is True for turn in turns)
    accepted = (
        len(turns) == len(context.acceptance_turns)
        and telemetry.get("accepted") is True
        and session_ok
        and transport_ok
    )
    return {
        "accepted": accepted,
        "reason": None if accepted else "native_agent_telemetry_acceptance_failed",
        "cli": cli,
        "turns": turns,
        "telemetry": telemetry,
        "gateway_transport_mode": "gateway_default_without_local_flag",
        "gateway_transport_proven": transport_ok,
        "gateway_transport_proven_by_plugin_telemetry": bool(telemetry.get("accepted")),
        "persisted_native_session": bool(telemetry.get("persisted_session")),
        "local_flag_used": False,
        "session_key_recorded": False,
        "conversation_content_recorded": False,
        "secret_values_recorded": False,
    }
