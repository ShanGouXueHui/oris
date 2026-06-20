from __future__ import annotations

from .task_contract import _native_support_tools
from .telemetry_analysis import evaluate_native_support_outcomes
from .telemetry_correlation import correlate_records
from .tool_authority import is_write_capable_tool


EVENTS = {"model_call_ended", "after_tool_call", "agent_end"}
TOOLS = {"sample_queue_tool", "sample_task_tool", "sample_latest_tool"}
SUPPORT_TOOL = "sample_skill_reader"
UNEXPECTED_TOOL = "sample_unapproved_tool"


def _records() -> list[dict]:
    records: list[dict] = []
    session_hash = "a" * 64
    for index, tool in enumerate(sorted(TOOLS)):
        run_hash = f"{index + 1:064x}"
        common = {"runHash": run_hash, "sessionHash": session_hash}
        records.extend(
            [
                {"event": "model_call_ended", **common},
                {"event": "after_tool_call", "toolName": tool, **common},
                {"event": "agent_end", **common},
            ]
        )
    return records


def _correlate(records: list[dict], max_calls: int = 1) -> dict:
    return correlate_records(
        records=records,
        expected_session_hashes={"a" * 64},
        expected_tools=TOOLS,
        expected_events=EVENTS,
        required_turns=3,
        same_cli_session_requested=True,
        native_support_tool_limits={SUPPORT_TOOL: max_calls},
    )


def test_native_support_tool_policy() -> None:
    one_support_call = _records() + [
        {
            "event": "after_tool_call",
            "toolName": SUPPORT_TOOL,
            "sessionHash": "a" * 64,
            "success": True,
        }
    ]
    accepted = _correlate(one_support_call)
    assert accepted["accepted"] is True
    assert accepted["native_support_tool_limits_ok"] is True
    assert accepted["native_support_tool_counts"] == {SUPPORT_TOOL: 1}
    assert accepted["unexpected_tools"] == set()

    excessive = _correlate(
        one_support_call
        + [
            {
                "event": "after_tool_call",
                "toolName": SUPPORT_TOOL,
                "sessionHash": "a" * 64,
                "success": True,
            }
        ]
    )
    assert excessive["accepted"] is False
    assert excessive["native_support_tool_limits_ok"] is False

    unexpected = _correlate(
        one_support_call
        + [
            {
                "event": "after_tool_call",
                "toolName": UNEXPECTED_TOOL,
                "sessionHash": "a" * 64,
                "success": True,
            }
        ]
    )
    assert unexpected["accepted"] is False
    assert UNEXPECTED_TOOL in unexpected["unexpected_tools"]

    support_success = evaluate_native_support_outcomes(
        one_support_call,
        {SUPPORT_TOOL},
    )
    assert support_success["ok"] is True

    support_failure = evaluate_native_support_outcomes(
        [
            {
                "event": "after_tool_call",
                "toolName": SUPPORT_TOOL,
                "success": False,
                "error": True,
            }
        ],
        {SUPPORT_TOOL},
    )
    assert support_failure["ok"] is False
    assert support_failure["failed_call_count"] == 1


def test_native_support_contract_validation() -> None:
    parsed = _native_support_tools(
        {
            "native_support_tools": [
                {
                    "name": SUPPORT_TOOL,
                    "max_calls": 1,
                    "purpose": "load one approved Skill body",
                }
            ]
        },
        tuple(sorted(TOOLS)),
        3,
    )
    assert parsed[0]["name"] == SUPPORT_TOOL
    assert parsed[0]["max_calls"] == 1
    assert is_write_capable_tool("exec") is True
    assert is_write_capable_tool(SUPPORT_TOOL) is False

    invalid_values = (
        {
            "native_support_tools": [
                {"name": "exec", "max_calls": 1, "purpose": "invalid"}
            ]
        },
        {
            "native_support_tools": [
                {
                    "name": sorted(TOOLS)[0],
                    "max_calls": 1,
                    "purpose": "overlap",
                }
            ]
        },
        {
            "native_support_tools": [
                {"name": SUPPORT_TOOL, "max_calls": 4, "purpose": "too many"}
            ]
        },
    )
    for value in invalid_values:
        try:
            _native_support_tools(value, tuple(sorted(TOOLS)), 3)
        except RuntimeError:
            continue
        raise AssertionError("invalid native support tool contract was accepted")
