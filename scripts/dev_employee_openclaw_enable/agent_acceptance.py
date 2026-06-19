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


def _json_output_valid(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    try:
        json.loads(stripped)
        return True
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            return False
        try:
            json.loads(stripped[start : end + 1])
            return True
        except json.JSONDecodeError:
            return False


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
    if session_flag is None or message_flag is None:
        raise RuntimeError("OpenClaw agent CLI lacks a supported session or message flag")
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
    if context.require_gateway_transport and not cli["local_flag_available"]:
        return _failed_result("gateway_transport_contract_unverifiable", cli)

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
        ]
        if cli["json_flag"]:
            command.append(str(cli["json_flag"]))
        started = time.perf_counter()
        result = run(command, timeout=context.turn_timeout_seconds)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        output_valid = (
            _json_output_valid(result.stdout)
            if cli["json_flag"]
            else bool(result.stdout.strip())
        )
        turns.append(
            {
                "intent": str(turn["intent"]),
                "expected_tool": str(turn["expected_tool"]),
                "returncode": result.returncode,
                "duration_ms": duration_ms,
                "output_present": bool(result.stdout.strip()),
                "structured_output_valid": output_valid,
                "stdout_bytes": len(result.stdout.encode("utf-8")),
                "stderr_bytes": len(result.stderr.encode("utf-8")),
            }
        )
        if result.returncode != 0 or not output_valid:
            failed = _failed_result("native_agent_turn_failed", cli)
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
    accepted = (
        len(turns) == len(context.acceptance_turns)
        and telemetry.get("accepted") is True
        and session_ok
    )
    return {
        "accepted": accepted,
        "reason": None if accepted else "native_agent_telemetry_acceptance_failed",
        "cli": cli,
        "turns": turns,
        "telemetry": telemetry,
        "gateway_transport_mode": "gateway_default_without_local_flag",
        "gateway_transport_proven_by_plugin_telemetry": bool(telemetry.get("accepted")),
        "persisted_native_session": bool(telemetry.get("persisted_session")),
        "local_flag_used": False,
        "session_key_recorded": False,
        "conversation_content_recorded": False,
        "secret_values_recorded": False,
    }
