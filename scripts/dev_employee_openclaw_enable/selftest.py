from __future__ import annotations

import copy

from .agent_output import reported_tool_names, session_identifier_hashes
from .agent_skill_policy import (
    ensure_skill_visible,
    resolve_default_agent_id,
    skill_is_visible,
    strip_authorized_skill_addition,
)
from .telemetry_correlation import correlate_records


EVENTS = {"model_call_ended", "after_tool_call", "agent_end"}
TOOLS = {"sample_queue_tool", "sample_task_tool", "sample_latest_tool"}
MISSING_TOOL = "sample_task_tool"
UNEXPECTED_TOOL = "sample_unapproved_tool"
SAMPLE_SKILL = "sample-routing-skill"


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


def _test_telemetry_correlation() -> None:
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


def _test_output_metadata() -> None:
    sample_tool = sorted(TOOLS)[0]
    payload = {
        "meta": {"sessionId": "private-session-id"},
        "events": [{"type": "tool_call", "toolName": sample_tool}],
    }
    hashes = session_identifier_hashes(payload)
    assert len(hashes) == 1
    assert "private-session-id" not in next(iter(hashes))
    assert reported_tool_names(payload, TOOLS) == {sample_tool}


def _test_agent_skill_policy() -> None:
    unrestricted: dict = {}
    unrestricted_change = ensure_skill_visible(unrestricted, SAMPLE_SKILL)
    assert unrestricted_change.unrestricted is True
    assert unrestricted_change.changed is False
    assert resolve_default_agent_id(unrestricted) == "main"
    assert skill_is_visible(unrestricted, SAMPLE_SKILL, "main") is True

    defaults = {"agents": {"defaults": {"skills": ["existing-skill"]}}}
    defaults_before = copy.deepcopy(defaults)
    defaults_change = ensure_skill_visible(defaults, SAMPLE_SKILL)
    assert defaults_change.scope == "defaults"
    assert defaults_change.changed is True
    assert skill_is_visible(defaults, SAMPLE_SKILL, "main") is True
    assert (
        strip_authorized_skill_addition(
            defaults,
            defaults_change,
            SAMPLE_SKILL,
        )
        == defaults_before
    )

    explicit = {
        "agents": {
            "defaults": {"skills": ["baseline-skill"]},
            "list": [
                {"id": "secondary", "skills": []},
                {"id": "primary", "default": True, "skills": ["agent-skill"]},
            ],
        }
    }
    explicit_before = copy.deepcopy(explicit)
    explicit_change = ensure_skill_visible(explicit, SAMPLE_SKILL)
    assert explicit_change.agent_id == "primary"
    assert explicit_change.scope == "agent"
    assert explicit_change.changed is True
    assert skill_is_visible(explicit, SAMPLE_SKILL, "primary") is True
    assert (
        strip_authorized_skill_addition(
            explicit,
            explicit_change,
            SAMPLE_SKILL,
        )
        == explicit_before
    )

    duplicate = {"agents": {"defaults": {"skills": ["same", "same"]}}}
    try:
        ensure_skill_visible(duplicate, SAMPLE_SKILL)
    except RuntimeError:
        pass
    else:
        raise AssertionError("duplicate skill allowlist entries must be rejected")


def run_selftests() -> bool:
    _test_telemetry_correlation()
    _test_output_metadata()
    _test_agent_skill_policy()
    return True
