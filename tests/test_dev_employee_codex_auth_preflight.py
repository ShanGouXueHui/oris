import tempfile
import unittest
from pathlib import Path

from scripts.dev_employee_codex_auth_preflight import (
    classify_codex_failure,
    run_codex_auth_preflight,
    sanitize_text,
)


class CodexAuthPreflightTests(unittest.TestCase):
    def test_refresh_token_reused_is_authentication_failure(self) -> None:
        text = "401 Unauthorized code=refresh_token_reused. Please log out and sign in again."
        self.assertEqual(classify_codex_failure(text, 1), "codex_authentication")

    def test_generic_nonzero_is_preflight_failure(self) -> None:
        self.assertEqual(classify_codex_failure("unexpected executor error", 1), "codex_preflight_failed")

    def test_sanitize_text_redacts_bearer_and_json_tokens(self) -> None:
        text = 'Authorization: Bearer abc123\n{"access_token":"secret-value"}'
        sanitized = sanitize_text(text)
        self.assertNotIn("abc123", sanitized)
        self.assertNotIn("secret-value", sanitized)
        self.assertIn("<REDACTED>", sanitized)

    def test_preflight_classifies_fake_executor_auth_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
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

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "preflight_failed")
            self.assertEqual(result["failure_code"], "codex_authentication")
            self.assertEqual(result["return_code"], 1)
            self.assertTrue(log_path.is_file())

    def test_preflight_accepts_fake_executor_success_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
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

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "ready")
            self.assertIsNone(result["failure_code"])
            self.assertTrue(result["marker_observed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
