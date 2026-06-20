from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .models import RuntimeContext
from .telemetry_analysis import (
    bounded_string_values,
    duration_stats,
    duration_values,
    evaluate_execution_outcomes,
)
from .telemetry_correlation import correlate_records


ALLOWED_KEYS = {
    "timestamp",
    "event",
    "durationMs",
    "outcome",
    "success",
    "error",
    "provider",
    "model",
    "toolName",
    "runHash",
    "callHash",
    "sessionHash",
}
FORBIDDEN_KEY = re.compile(
    r"prompt|message|content|text|argument|result|header|token|password|secret|credential|cookie|authorization|api.?key",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
)


def _mode_owner_ok(path: Path, expected_mode: int) -> bool:
    if not path.exists():
        return True
    stat = path.stat()
    return stat.st_uid == Path.home().stat().st_uid and (stat.st_mode & 0o777) == expected_mode


def _record_schema_ok(item: dict[str, Any], expected_events: set[str]) -> bool:
    keys = set(item)
    if not keys.issubset(ALLOWED_KEYS) or any(
        FORBIDDEN_KEY.search(key) for key in keys
    ):
        return False
    timestamp = item.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        return False
    if item.get("event") not in expected_events:
        return False
    for key in ("runHash", "callHash", "sessionHash"):
        if key in item and not re.fullmatch(r"[0-9a-f]{64}", str(item[key])):
            return False
    duration = item.get("durationMs")
    if duration is not None and (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or duration < 0
    ):
        return False
    for key in ("success", "error"):
        if key in item and not isinstance(item[key], bool):
            return False
    for key in ("outcome", "provider", "model", "toolName"):
        if key in item and (
            not isinstance(item[key], str)
            or not item[key]
            or len(item[key]) > 160
        ):
            return False
    return True


def _read_records(
    context: RuntimeContext,
    started_at: str,
) -> tuple[list[dict[str, Any]], bool, bool]:
    records: list[dict[str, Any]] = []
    schema_ok = True
    content_safe = True
    current = context.telemetry_path
    rotated = Path(str(current) + ".1")
    expected_events = set(context.required_hooks)
    for candidate in (rotated, current):
        if not candidate.exists():
            continue
        raw = candidate.read_text(encoding="utf-8", errors="replace")
        if any(pattern.search(raw) for pattern in SECRET_PATTERNS):
            content_safe = False
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                schema_ok = False
                continue
            if not isinstance(item, dict):
                schema_ok = False
                continue
            timestamp = item.get("timestamp")
            if isinstance(timestamp, str) and timestamp < started_at:
                continue
            if not _record_schema_ok(item, expected_events):
                schema_ok = False
            records.append(item)
    return records, schema_ok, content_safe


def inspect_telemetry(
    context: RuntimeContext,
    started_at: str,
    session_key: str,
    output_session_hashes: set[str] | None = None,
    same_cli_session_requested: bool = False,
) -> dict[str, Any]:
    expected_events = set(context.required_hooks)
    expected_tools = set(context.approved_tools)
    expected_session_hashes = {
        hashlib.sha256(session_key.encode("utf-8")).hexdigest()
    }
    expected_session_hashes.update(output_session_hashes or set())

    records, schema_ok, content_safe = _read_records(context, started_at)
    correlation = correlate_records(
        records=records,
        expected_session_hashes=expected_session_hashes,
        expected_tools=expected_tools,
        expected_events=expected_events,
        required_turns=len(context.acceptance_turns),
        same_cli_session_requested=same_cli_session_requested,
    )
    relevant_records = correlation["correlated_records"]
    tools_seen = set(correlation["tools_seen"])
    unexpected_tools = set(correlation["unexpected_tools"])
    outcomes = evaluate_execution_outcomes(relevant_records, expected_tools)
    current = context.telemetry_path
    rotated = Path(str(current) + ".1")
    parent_permissions_ok = _mode_owner_ok(current.parent, 0o700)
    file_permissions_ok = _mode_owner_ok(current, 0o600) and _mode_owner_ok(
        rotated,
        0o600,
    )
    accepted = bool(
        correlation["accepted"]
        and outcomes["ok"]
        and schema_ok
        and content_safe
        and parent_permissions_ok
        and file_permissions_ok
    )
    return {
        "accepted": accepted,
        "expected_tools_seen": sorted(expected_tools.intersection(tools_seen)),
        "unexpected_tools_seen": sorted(unexpected_tools),
        "only_approved_tools_used": not unexpected_tools,
        "execution_outcome_ok": bool(outcomes["ok"]),
        "execution_outcomes": outcomes,
        "event_counts": correlation["event_counts"],
        "all_event_counts": correlation["all_event_counts"],
        "all_tools_seen": sorted(correlation["all_tools_seen"]),
        "providers_seen": bounded_string_values(relevant_records, "provider"),
        "models_seen": bounded_string_values(relevant_records, "model"),
        "persisted_session": bool(correlation["persisted_session"]),
        "session_hash_matched": bool(correlation["matched_session_records"]),
        "correlation_mode": correlation["correlation_mode"],
        "observed_session_hash_count": correlation["observed_session_hash_count"],
        "same_cli_session_requested": correlation["same_cli_session_requested"],
        "exact_agent_turn_boundary": correlation["exact_agent_turn_boundary"],
        "isolated_window_fallback_used": correlation[
            "isolated_window_fallback_used"
        ],
        "run_hash_correlation_used": any(
            item.get("runHash") for item in relevant_records
        ),
        "schema_ok": schema_ok,
        "content_safe": content_safe,
        "parent_permissions_ok": parent_permissions_ok,
        "file_permissions_ok": file_permissions_ok,
        "records_after_start": len(records),
        "correlated_records": len(relevant_records),
        "session_records": len(correlation["matched_session_records"]),
        "metrics": {
            "ttft": {
                "available": False,
                "reason": "approved typed hooks do not expose a first-token timestamp",
            },
            "model_duration": duration_stats(
                duration_values(relevant_records, "model_call_ended")
            ),
            "total_agent_duration": duration_stats(
                duration_values(relevant_records, "agent_end")
            ),
            "tool_duration": {
                tool: duration_stats(
                    duration_values(relevant_records, "after_tool_call", tool)
                )
                for tool in sorted(expected_tools)
            },
        },
        "secret_values_recorded": False,
        "conversation_content_recorded": False,
    }
