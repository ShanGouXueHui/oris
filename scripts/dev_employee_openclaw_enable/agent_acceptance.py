from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

from .agent_output import (
    effective_tool_surface,
    find_transport_metadata,
    parse_json_output,
    reported_tool_names,
    session_identifier_hashes,
)
from .agent_skill_policy import resolve_default_agent_id
from .models import RuntimeContext
from .process import run
from .state import load_json
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
        raise RuntimeError(
            "OpenClaw agent CLI lacks required session, message, or JSON flags"
        )
    return {
        "session_flag": session_flag,
        "message_flag": message_flag,
        "json_flag": json_flag,
        "agent_flag_available": "--agent" in help_text,
        "local_flag_available": "--local" in help_text,
        "pre_mutation_selftests_required": True,
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


def _agent_command(
    cli: dict[str, Any],
    agent_id: str,
    session_key: str,
    message: str,
) -> list[str]:
    command = ["openclaw", "agent"]
    if cli.get("agent_flag_available") is True:
        command.extend(["--agent", agent_id])
    command.extend(
        [
            str(cli["session_flag"]),
            session_key,
            str(cli["message_flag"]),
            message,
            str(cli["json_flag"]),
        ]
    )
    return command


def _merge_surfaces(surfaces: list[dict[str, Any]], approved: set[str]) -> dict[str, Any]:
    checked = [item for item in surfaces if item.get("status") != "NOT_CHECKED"]
    present = {
        name
        for item in checked
        for name in item.get("approved_tools_present", [])
        if isinstance(name, str)
    }
    missing = approved - present
    return {
        "status": "NOT_CHECKED" if not checked else "PASS" if not missing else "FAIL",
        "reports_observed": sum(int(item.get("report_count") or 0) for item in surfaces),
        "max_total_tool_count": max(
            [int(item.get("total_tool_count") or 0) for item in surfaces] or [0]
        ),
        "approved_tools_present": sorted(present),
        "missing_approved_tools": sorted(missing),
        "routing_skill_present": any(
            item.get("routing_skill_present") is True for item in checked
        ),
        "other_tool_names_recorded": False,
        "system_prompt_recorded": False,
        "conversation_content_recorded": False,
    }


def run_automatic_acceptance(context: RuntimeContext, stamp: str) -> dict[str, Any]:
    cli = discover_agent_cli()
    agent_id = resolve_default_agent_id(load_json(context.openclaw_config))
    session_key = f"{context.session_prefix}-{stamp.lower()}"
    started_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00",
        "Z",
    )
    approved_tools = set(context.approved_tools)
    turns: list[dict[str, Any]] = []
    surfaces: list[dict[str, Any]] = []
    output_session_hashes: set[str] = set()
    for turn in context.acceptance_turns:
        message = str(turn["message_template"]).format(task_id=context.task_id)
        command = _agent_command(cli, agent_id, session_key, message)
        started = time.perf_counter()
        result = run(command, timeout=context.turn_timeout_seconds)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        payload = parse_json_output(result.stdout)
        transport, fallback_from = find_transport_metadata(payload)
        embedded_fallback = transport == "embedded" or fallback_from == "gateway"
        gateway_transport_ok = not embedded_fallback
        payload_session_hashes = session_identifier_hashes(payload)
        output_session_hashes.update(payload_session_hashes)
        payload_tools = reported_tool_names(payload, approved_tools)
        surface = effective_tool_surface(
            payload,
            approved_tools,
            context.routing_skill_name,
        )
        surfaces.append(surface)
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
                "reported_tool_names": sorted(payload_tools),
                "effective_tool_surface_status": surface["status"],
                "effective_approved_tool_count": len(
                    surface["approved_tools_present"]
                ),
                "session_identifier_hash_count": len(payload_session_hashes),
                "stdout_bytes": len(result.stdout.encode("utf-8")),
                "stderr_bytes": len(result.stderr.encode("utf-8")),
            }
        )
        if result.returncode != 0 or payload is None or (
            context.require_gateway_transport and not gateway_transport_ok
        ):
            failed = _failed_result(
                "embedded_fallback_rejected"
                if embedded_fallback
                else "native_agent_turn_failed",
                cli,
            )
            failed["turns"] = turns
            failed["agent_id"] = agent_id
            failed["effective_tool_surface"] = _merge_surfaces(
                surfaces,
                approved_tools,
            )
            return failed

    effective_surface = _merge_surfaces(surfaces, approved_tools)
    same_cli_session_requested = len(turns) == len(context.acceptance_turns)
    deadline = time.monotonic() + context.telemetry_wait_seconds
    telemetry: dict[str, Any] = {}
    while time.monotonic() < deadline:
        telemetry = inspect_telemetry(
            context,
            started_at,
            session_key,
            output_session_hashes=output_session_hashes,
            same_cli_session_requested=same_cli_session_requested,
        )
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
        and effective_surface.get("status") != "FAIL"
    )
    reason = None
    if not accepted:
        reason = (
            "approved_tools_missing_from_effective_model_surface"
            if effective_surface.get("status") == "FAIL"
            else "native_agent_telemetry_acceptance_failed"
        )
    return {
        "accepted": accepted,
        "reason": reason,
        "cli": cli,
        "agent_id": agent_id,
        "agent_targeted_explicitly": bool(cli.get("agent_flag_available")),
        "turns": turns,
        "effective_tool_surface": effective_surface,
        "telemetry": telemetry,
        "gateway_transport_mode": "gateway_default_without_local_flag",
        "gateway_transport_proven": transport_ok,
        "gateway_transport_proven_by_plugin_telemetry": bool(
            telemetry.get("accepted")
        ),
        "persisted_native_session": bool(telemetry.get("persisted_session")),
        "same_cli_session_requested": same_cli_session_requested,
        "output_session_hash_count": len(output_session_hashes),
        "local_flag_used": False,
        "session_key_recorded": False,
        "conversation_content_recorded": False,
        "secret_values_recorded": False,
    }
