from scripts.dev_employee_task_states import canonical_status, classify, is_terminal_status


def test_legacy_codex_failed_is_terminal_failed() -> None:
    result = classify("codex_failed")
    assert result == {
        "status": "codex_failed",
        "canonical_status": "failed",
        "terminal": True,
        "failure_code": "codex_failed",
    }


def test_blocked_family_is_terminal() -> None:
    assert canonical_status("blocked_result_schema_invalid") == "blocked"
    assert is_terminal_status("blocked_result_schema_invalid") is True


def test_active_states_are_not_terminal() -> None:
    for status in ["accepted", "validated", "queued", "claimed", "planning", "executing"]:
        assert is_terminal_status(status) is False


def test_completed_and_preflight_failed_are_terminal() -> None:
    assert is_terminal_status("completed") is True
    assert is_terminal_status("preflight_failed") is True
