from pathlib import Path

from scripts.dev_employee_codex_auth_preflight import (
    classify_codex_failure,
    run_codex_auth_preflight,
    sanitize_text,
)


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


def test_preflight_classifies_fake_executor_auth_failure(tmp_path: Path) -> None:
    fake_codex = tmp_path / "codex"
    fake_codex.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 'codex-cli test'\n"
        "  exit 0\n"
        "fi\n"
        "echo '401 Unauthorized: refresh_token_reused; please log out and sign in again' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)
    log_path = tmp_path / "preflight.json"

    result = run_codex_auth_preflight(fake_codex, tmp_path, log_path=log_path, timeout=10)

    assert result["ok"] is False
    assert result["status"] == "preflight_failed"
    assert result["failure_code"] == "codex_authentication"
    assert result["return_code"] == 1
    assert log_path.is_file()


def test_preflight_accepts_fake_executor_success_marker(tmp_path: Path) -> None:
    fake_codex = tmp_path / "codex"
    fake_codex.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 'codex-cli test'\n"
        "  exit 0\n"
        "fi\n"
        "echo 'ORIS_CODEX_AUTH_OK'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    result = run_codex_auth_preflight(fake_codex, tmp_path, timeout=10)

    assert result["ok"] is True
    assert result["status"] == "ready"
    assert result["failure_code"] is None
    assert result["marker_observed"] is True
