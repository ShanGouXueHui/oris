from __future__ import annotations

import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

from .models import RuntimeContext


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


def _duration_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"available": False, "count": 0}
    return {
        "available": True,
        "count": len(values),
        "min_ms": round(min(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "max_ms": round(max(values), 3),
    }


def inspect_telemetry(
    context: RuntimeContext,
    started_at: str,
    session_key: str,
) -> dict[str, Any]:
    expected_events = set(context.required_hooks)
    expected_tools = set(context.approved_tools)
    session_hash = hashlib.sha256(session_key.encode("utf-8")).hexdigest()
    records: list[dict[str, Any]] = []
    schema_ok = True
    content_safe = True
    current = context.telemetry_path
    rotated = Path(str(current) + ".1")

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
            if str(item.get("timestamp") or "") < started_at:
                continue
            keys = set(item)
            if not keys.issubset(ALLOWED_KEYS) or any(FORBIDDEN_KEY.search(key) for key in keys):
                schema_ok = False
            if item.get("event") not in expected_events:
                schema_ok = False
            for key in ("runHash", "callHash", "sessionHash"):
                if key in item and not re.fullmatch(r"[0-9a-f]{64}", str(item[key])):
                    schema_ok = False
            duration = item.get("durationMs")
            if duration is not None and (
                not isinstance(duration, (int, float)) or duration < 0
            ):
                schema_ok = False
            if item.get("error") is True or item.get("success") is False:
                schema_ok = False
            records.append(item)

    session_records = [item for item in records if item.get("sessionHash") == session_hash]
    relevant_records = session_records or records
    tools_seen = {
        str(item.get("toolName"))
        for item in relevant_records
        if item.get("event") == "after_tool_call" and isinstance(item.get("toolName"), str)
    }
    event_counts = {
        event: sum(item.get("event") == event for item in relevant_records)
        for event in expected_events
    }
    model_durations = [
        float(item["durationMs"])
        for item in relevant_records
        if item.get("event") == "model_call_ended"
        and isinstance(item.get("durationMs"), (int, float))
    ]
    agent_durations = [
        float(item["durationMs"])
        for item in relevant_records
        if item.get("event") == "agent_end"
        and isinstance(item.get("durationMs"), (int, float))
    ]
    tool_durations = {
        tool: [
            float(item["durationMs"])
            for item in relevant_records
            if item.get("event") == "after_tool_call"
            and item.get("toolName") == tool
            and isinstance(item.get("durationMs"), (int, float))
        ]
        for tool in sorted(expected_tools)
    }
    parent_permissions_ok = _mode_owner_ok(current.parent, 0o700)
    file_permissions_ok = _mode_owner_ok(current, 0o600) and _mode_owner_ok(rotated, 0o600)
    persisted_session = len(session_records) >= 3 and event_counts.get("agent_end", 0) >= 3
    accepted = (
        expected_tools.issubset(tools_seen)
        and all(event_counts.get(event, 0) >= 3 for event in ("model_call_ended", "agent_end"))
        and event_counts.get("after_tool_call", 0) >= 3
        and persisted_session
        and schema_ok
        and content_safe
        and parent_permissions_ok
        and file_permissions_ok
    )
    return {
        "accepted": accepted,
        "expected_tools_seen": sorted(expected_tools.intersection(tools_seen)),
        "event_counts": event_counts,
        "persisted_session": persisted_session,
        "session_hash_matched": bool(session_records),
        "schema_ok": schema_ok,
        "content_safe": content_safe,
        "parent_permissions_ok": parent_permissions_ok,
        "file_permissions_ok": file_permissions_ok,
        "records_after_start": len(records),
        "session_records": len(session_records),
        "metrics": {
            "ttft": {
                "available": False,
                "reason": "approved typed hooks do not expose a first-token timestamp",
            },
            "model_duration": _duration_stats(model_durations),
            "total_agent_duration": _duration_stats(agent_durations),
            "tool_duration": {
                tool: _duration_stats(values)
                for tool, values in tool_durations.items()
            },
        },
        "secret_values_recorded": False,
        "conversation_content_recorded": False,
    }
