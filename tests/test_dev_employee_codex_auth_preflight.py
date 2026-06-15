from scripts.dev_employee_codex_auth_preflight import classify_codex_failure, sanitize_text


def test_refresh_token_reused_is_authentication_failure() -> None:
    text = "401 Unauthorized code=refresh_token_reused. Please log out and sign in again."
    assert classify_codex_failure(text, 1) == "codex_authentication"


def test_generic_nonzero_is_preflight_failure() -> None:
    assert classify_codex_failure("unexpected executor error", 1) == "codex_preflight_failed"


def test_sanitize_text_redacts_bearer_and_json_tokens() -> None:
    text = 'Authorization: Bearer abc123\n{"access_token":"secret-value"}'
    sanitized = sanitize_text(text)
    assert "abc123" not in sanitized
    assert "secret-value" not in sanitized
    assert "<REDACTED>" in sanitized
