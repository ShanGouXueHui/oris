from __future__ import annotations

from collections import Counter
from typing import Any


def _event_counts(
    records: list[dict[str, Any]],
    expected_events: set[str],
) -> dict[str, int]:
    return {
        event: sum(item.get("event") == event for item in records)
        for event in expected_events
    }


def _tool_names(records: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("toolName"))
        for item in records
        if item.get("event") == "after_tool_call"
        and isinstance(item.get("toolName"), str)
    }


def _tool_counts(records: list[dict[str, Any]]) -> Counter[str]:
    return Counter(
        str(item.get("toolName"))
        for item in records
        if item.get("event") == "after_tool_call"
        and isinstance(item.get("toolName"), str)
    )


def _append_unique(
    target: list[dict[str, Any]],
    additions: list[dict[str, Any]],
) -> None:
    identities = {id(item) for item in target}
    for item in additions:
        if id(item) not in identities:
            target.append(item)
            identities.add(id(item))


def correlate_records(
    records: list[dict[str, Any]],
    expected_session_hashes: set[str],
    expected_tools: set[str],
    expected_events: set[str],
    required_turns: int,
    same_cli_session_requested: bool,
    native_support_tool_limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    support_limits = dict(native_support_tool_limits or {})
    support_tools = set(support_limits)
    authorized_tools = expected_tools | support_tools
    all_event_counts = _event_counts(records, expected_events)
    all_tools_seen = _tool_names(records)
    matched_session_records = [
        item
        for item in records
        if isinstance(item.get("sessionHash"), str)
        and item.get("sessionHash") in expected_session_hashes
    ]
    run_hashes = {
        str(item["runHash"])
        for item in matched_session_records
        if isinstance(item.get("runHash"), str)
    }
    correlated = [
        item
        for item in records
        if item in matched_session_records
        or (
            isinstance(item.get("runHash"), str)
            and item.get("runHash") in run_hashes
        )
    ]
    correlation_mode = "session_hash" if correlated else "none"

    observed_session_hashes = {
        str(item["sessionHash"])
        for item in records
        if isinstance(item.get("sessionHash"), str)
    }
    if not correlated and len(observed_session_hashes) == 1:
        only_hash = next(iter(observed_session_hashes))
        correlated = [
            item
            for item in records
            if item.get("sessionHash") == only_hash or not item.get("sessionHash")
        ]
        correlation_mode = "isolated_unique_session_hash"
    elif not correlated and not observed_session_hashes:
        correlated = list(records)
        correlation_mode = "isolated_time_window"

    initial_tools_seen = _tool_names(correlated)
    missing_tools = expected_tools - initial_tools_seen
    window_is_single_agent = (
        same_cli_session_requested
        and all_event_counts.get("agent_end", 0) == required_turns
        and len(observed_session_hashes) <= 1
    )
    if correlated and missing_tools and window_is_single_agent:
        window_tool_records = [
            item for item in records if item.get("event") == "after_tool_call"
        ]
        _append_unique(correlated, window_tool_records)
        correlation_mode += "+isolated_window_tools"

    event_counts = _event_counts(correlated, expected_events)
    tools_seen = _tool_names(correlated)
    tool_counts = _tool_counts(correlated)
    unexpected_tools = tools_seen - authorized_tools
    support_tools_seen = tools_seen.intersection(support_tools)
    support_tool_counts = {
        name: tool_counts.get(name, 0) for name in sorted(support_tools)
    }
    support_limits_ok = all(
        support_tool_counts[name] <= support_limits[name]
        for name in support_tool_counts
    )
    agent_end_count = event_counts.get("agent_end", 0)
    model_count = event_counts.get("model_call_ended", 0)
    tool_count = event_counts.get("after_tool_call", 0)

    exact_agent_turn_boundary = agent_end_count == required_turns
    typed_tools_complete = expected_tools.issubset(tools_seen)
    tool_authority_valid = not unexpected_tools and support_limits_ok
    hooks_complete = (
        model_count >= required_turns
        and tool_count >= required_turns
        and exact_agent_turn_boundary
    )
    fallback_mode = (
        correlation_mode.startswith("isolated_")
        or "+isolated_window_tools" in correlation_mode
    )
    fallback_safe = (
        fallback_mode
        and window_is_single_agent
        and hooks_complete
        and typed_tools_complete
        and tool_authority_valid
    )
    persisted_session = (
        agent_end_count >= required_turns
        and (
            correlation_mode.startswith("session_hash")
            or correlation_mode.startswith("isolated_unique_session_hash")
            or fallback_safe
        )
    )
    accepted = (
        hooks_complete
        and typed_tools_complete
        and tool_authority_valid
        and persisted_session
    )

    return {
        "accepted": accepted,
        "correlated_records": correlated,
        "matched_session_records": matched_session_records,
        "correlation_mode": correlation_mode,
        "event_counts": event_counts,
        "all_event_counts": all_event_counts,
        "tools_seen": tools_seen,
        "all_tools_seen": all_tools_seen,
        "native_support_tools_seen": support_tools_seen,
        "native_support_tool_counts": support_tool_counts,
        "native_support_tool_limits_ok": support_limits_ok,
        "unexpected_tools": unexpected_tools,
        "observed_session_hash_count": len(observed_session_hashes),
        "persisted_session": persisted_session,
        "same_cli_session_requested": same_cli_session_requested,
        "exact_agent_turn_boundary": exact_agent_turn_boundary,
        "isolated_window_fallback_used": fallback_safe,
    }
