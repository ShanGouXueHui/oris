from __future__ import annotations

from .effective_surface_inventory_selftest import (
    test_effective_surface_inventory_sanitizer,
)
from .effective_tool_surface import summarize_effective_tool_payload


_APPROVED = (
    "oris_queue_status",
    "oris_task_status",
    "oris_latest_task_status",
)
_PLUGIN_ID = "oris-dev-employee"


def _tool(name: str, source: str = "plugin", plugin_id: str = _PLUGIN_ID) -> dict:
    return {
        "id": name,
        "source": source,
        "pluginId": plugin_id,
        "description": "must not be retained",
    }


def test_effective_tool_surface_parser() -> None:
    payload = {
        "agentId": "main",
        "profile": "coding",
        "groups": [
            {
                "id": "core",
                "tools": [
                    _tool("session_status", "core", ""),
                    _tool("write", "core", ""),
                ],
            },
            {
                "id": "plugin",
                "tools": [_tool(name) for name in _APPROVED],
            },
        ],
    }
    summary = summarize_effective_tool_payload(payload, _APPROVED, _PLUGIN_ID)
    assert summary["status"] == "PASS"
    assert summary["profile"] == "coding"
    assert summary["approved_tools_present"] == sorted(_APPROVED)
    assert summary["missing_approved_tools"] == []
    assert summary["all_approved_tools_plugin_owned"] is True
    assert summary["write_capable_core_tools_present"] is True
    assert summary["tool_descriptions_recorded"] is False
    assert "must not be retained" not in str(summary)

    missing = {
        "profile": "coding",
        "groups": [{"id": "plugin", "tools": [_tool(_APPROVED[0])]}],
    }
    missing_summary = summarize_effective_tool_payload(
        {"payload": missing},
        _APPROVED,
        _PLUGIN_ID,
    )
    assert missing_summary["status"] == "FAIL"
    assert missing_summary["missing_approved_tools"] == sorted(_APPROVED[1:])

    wrong_owner = {
        "profile": "coding",
        "groups": [
            {
                "id": "plugin",
                "tools": [
                    _tool(_APPROVED[0], plugin_id="other-plugin"),
                    _tool(_APPROVED[1]),
                    _tool(_APPROVED[2]),
                ],
            }
        ],
    }
    owner_summary = summarize_effective_tool_payload(
        wrong_owner,
        _APPROVED,
        _PLUGIN_ID,
    )
    assert owner_summary["status"] == "FAIL"
    assert owner_summary["wrong_owner_approved_tools"] == [_APPROVED[0]]
    test_effective_surface_inventory_sanitizer()
