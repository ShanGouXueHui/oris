from __future__ import annotations

import statistics
from collections import Counter
from typing import Any


def duration_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"available": False, "count": 0}
    return {
        "available": True,
        "count": len(values),
        "min_ms": round(min(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "max_ms": round(max(values), 3),
    }


def duration_values(
    records: list[dict[str, Any]],
    event_name: str,
    tool_name: str | None = None,
) -> list[float]:
    values: list[float] = []
    for item in records:
        if item.get("event") != event_name:
            continue
        if tool_name is not None and item.get("toolName") != tool_name:
            continue
        duration = item.get("durationMs")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            values.append(float(duration))
    return values


def bounded_string_values(
    records: list[dict[str, Any]],
    key: str,
) -> list[str]:
    values: set[str] = set()
    for item in records:
        value = item.get(key)
        if isinstance(value, str) and value and len(value) <= 160:
            values.add(value)
    return sorted(values)


def record_failed(item: dict[str, Any]) -> bool:
    return item.get("error") is True or item.get("success") is False


def evaluate_execution_outcomes(
    records: list[dict[str, Any]],
    expected_tools: set[str],
) -> dict[str, Any]:
    tool_records = [
        item
        for item in records
        if item.get("event") == "after_tool_call"
        and isinstance(item.get("toolName"), str)
    ]
    successful_tools = {
        str(item["toolName"])
        for item in tool_records
        if not record_failed(item)
    }
    tool_attempt_counts = Counter(str(item["toolName"]) for item in tool_records)
    failed_event_counts = Counter(
        str(item.get("event")) for item in records if record_failed(item)
    )
    missing_successful_tools = expected_tools - successful_tools
    failed_agent_end_count = failed_event_counts.get("agent_end", 0)
    return {
        "ok": not missing_successful_tools and failed_agent_end_count == 0,
        "successful_expected_tools": sorted(expected_tools.intersection(successful_tools)),
        "missing_successful_tools": sorted(missing_successful_tools),
        "failed_event_counts": dict(sorted(failed_event_counts.items())),
        "failed_event_count": sum(failed_event_counts.values()),
        "failed_agent_end_count": failed_agent_end_count,
        "retry_tools": sorted(
            tool for tool, count in tool_attempt_counts.items() if count > 1
        ),
        "tool_attempt_counts": {
            tool: tool_attempt_counts.get(tool, 0) for tool in sorted(expected_tools)
        },
        "tool_arguments_or_results_recorded": False,
        "conversation_content_recorded": False,
    }
