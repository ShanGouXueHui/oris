from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from .agent_output import reported_tool_names, session_identifier_hashes
from .telemetry import _read_records
from .telemetry_analysis import evaluate_execution_outcomes
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


def test_telemetry_correlation() -> None:
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
        item for item in _records() if item.get("toolName") != MISSING_TOOL
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


def test_telemetry_schema_and_outcomes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        telemetry_path = Path(directory) / "latency.jsonl"
        telemetry_path.write_text(
            json.dumps(
                {
                    "timestamp": "2026-06-20T20:00:01.000Z",
                    "event": "after_tool_call",
                    "toolName": MISSING_TOOL,
                    "success": False,
                    "error": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        context = SimpleNamespace(
            telemetry_path=telemetry_path,
            required_hooks=tuple(EVENTS),
        )
        records, schema_ok, content_safe = _read_records(
            context,
            "2026-06-20T20:00:00.000Z",
        )
        assert len(records) == 1
        assert schema_ok is True
        assert content_safe is True

    retry_records = _records()
    retry_records.append(
        {
            "event": "after_tool_call",
            "toolName": MISSING_TOOL,
            "success": False,
            "error": True,
        }
    )
    retry = evaluate_execution_outcomes(retry_records, TOOLS)
    assert retry["ok"] is True
    assert retry["failed_event_count"] == 1
    assert MISSING_TOOL in retry["retry_tools"]

    failed_tool_records = [
        {
            **item,
            "success": False,
            "error": True,
        }
        if item.get("event") == "after_tool_call"
        and item.get("toolName") == MISSING_TOOL
        else item
        for item in _records()
    ]
    failed_tool = evaluate_execution_outcomes(failed_tool_records, TOOLS)
    assert failed_tool["ok"] is False
    assert MISSING_TOOL in failed_tool["missing_successful_tools"]

    failed_agent_records = [
        {**item, "success": False}
        if item.get("event") == "agent_end" and index == 2
        else item
        for index, item in enumerate(_records())
    ]
    failed_agent = evaluate_execution_outcomes(failed_agent_records, TOOLS)
    assert failed_agent["ok"] is False
    assert failed_agent["failed_agent_end_count"] == 1


def test_output_metadata() -> None:
    sample_tool = sorted(TOOLS)[0]
    payload = {
        "meta": {"sessionId": "private-session-id"},
        "events": [{"type": "tool_call", "toolName": sample_tool}],
    }
    hashes = session_identifier_hashes(payload)
    assert len(hashes) == 1
    assert "private-session-id" not in next(iter(hashes))
    assert reported_tool_names(payload, TOOLS) == {sample_tool}
