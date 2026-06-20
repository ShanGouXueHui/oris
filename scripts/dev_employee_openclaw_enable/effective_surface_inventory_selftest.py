from __future__ import annotations

from .effective_surface_inventory import sanitize_effective_tool_surface


_APPROVED = (
    "oris_queue_status",
    "oris_task_status",
    "oris_latest_task_status",
)


def test_effective_surface_inventory_sanitizer() -> None:
    raw = {
        "status": "PASS",
        "reason_code": None,
        "profile": "coding",
        "group_count": 2,
        "total_tool_count": 12,
        "plugin_tool_count": 3,
        "approved_tool_count": 3,
        "approved_tools_present": [*_APPROVED, "unapproved_tool"],
        "wrong_owner_approved_tools": [],
        "output_sha256": "must-not-survive",
        "write_capable_core_tools_present": True,
        "description": "must-not-survive",
    }
    sanitized = sanitize_effective_tool_surface(raw, _APPROVED)
    assert sanitized["status"] == "PASS"
    assert sanitized["approved_tools_present"] == sorted(_APPROVED)
    assert sanitized["approved_tool_ownership"] == {
        name: True for name in sorted(_APPROVED)
    }
    assert sanitized["non_approved_tool_names_recorded"] is False
    assert "unapproved_tool" not in str(sanitized)
    assert "output_sha256" not in sanitized
    assert "write_capable_core_tools_present" not in sanitized
    assert "description" not in sanitized

    wrong_owner = dict(raw)
    wrong_owner["status"] = "FAIL"
    wrong_owner["wrong_owner_approved_tools"] = [_APPROVED[0]]
    wrong_owner["reason_code"] = "approved_tools_absent_from_effective_surface"
    sanitized_owner = sanitize_effective_tool_surface(wrong_owner, _APPROVED)
    assert sanitized_owner["status"] == "FAIL"
    assert sanitized_owner["approved_tool_ownership"][_APPROVED[0]] is False

    rpc_failure = sanitize_effective_tool_surface(
        {
            "status": "FAIL",
            "reason_code": "tools_effective_rpc_failed",
            "command_returncode": 1,
            "stdout_bytes": 0,
            "stderr_bytes": 20,
        },
        _APPROVED,
    )
    assert rpc_failure["status"] == "FAIL"
    assert rpc_failure["reason_code"] == "tools_effective_rpc_failed"
    assert rpc_failure["missing_approved_tools"] == sorted(_APPROVED)
