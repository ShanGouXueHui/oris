from __future__ import annotations

from .agent_output import reported_tool_names, session_identifier_hashes
from .telemetry_correlation import correlate_records


EVENTS = {"model_call_ended", "after_tool_call", "agent_end"}
TOOLS = {"sample_queue_tool", "sample_task_tool", "sample_latest_tool"}
MISSING_TOOL = "sample_task_tool"
UNEXPECTED_TOOL = "sample_unapproved_tool"


def _records(session_hash: str | None = None) -> list[dict]:
    values: list[dict] = []
    for index, tool in enumerate(sorted(TOOLS)):
        run_hash = f"{index + 1:064x}"
        common = {"runHash": run_hash}
        if session_hash is not None:
            common["sessionHash"] = session_hash
        values.extend(
            [
                {"event": "model_call_ended", **common},
                {"event": "after_tool_call", "toolName": tool, **common},
                {"event": "agent_end", **common},
            ]
        )
    return values


def run_selftests() -> bool:
    session_hash = "a" * 64
    direct = correlate_records(
        records=_records(session_hash),
        expected_session_hashes={session_hash},
        expected_tools=TOOLS,
        expected_events=EVENTS,
        required_turns=3,
        same_cli_session_requested=True,
    )
    assert direct["accepted"] is True
    assert direct["correlation_mode"] == "session_hash"

    isolated = correlate_records(
        records=_records(),
        expected_session_hashes={"b" * 64},
        expected_tools=TOOLS,
        expected_events=EVENTS,
        required_turns=3,
        same_cli_session_requested=True,
    )
    assert isolated["accepted"] is True
    assert isolated["isolated_window_fallback_used"] is True

    missing_tool_records = [
        item
        for item in _records()
        if item.get("toolName") != MISSING_TOOL
    ]
    missing = correlate_records(
        records=missing_tool_records,
        expected_session_hashes=set(),
        expected_tools=TOOLS,
        expected_events=EVENTS,
        required_turns=3,
        same_cli_session_requested=True,
    )
    assert missing["accepted"] is False

    unexpected_records = _records()
    unexpected_records.append(
        {"event": "after_tool_call", "toolName": UNEXPECTED_TOOL}
    )
    unexpected = correlate_records(
        records=unexpected_records,
        expected_session_hashes=set(),
        expected_tools=TOOLS,
        expected_events=EVENTS,
        required_turns=3,
        same_cli_session_requested=True,
    )
    assert unexpected["accepted"] is False
    assert UNEXPECTED_TOOL in unexpected["unexpected_tools"]

    sample_tool = sorted(TOOLS)[0]
    payload = {
        "meta": {"sessionId": "private-session-id"},
        "events": [{"type": "tool_call", "toolName": sample_tool}],
    }
    hashes = session_identifier_hashes(payload)
    assert len(hashes) == 1
    assert "private-session-id" not in next(iter(hashes))
    assert reported_tool_names(payload, TOOLS) == {sample_tool}
    return True
