import unittest

from scripts.dev_employee_task_states import canonical_status, classify, is_terminal_status


class TaskStateTests(unittest.TestCase):
    def test_legacy_codex_failed_is_terminal_failed(self) -> None:
        result = classify("codex_failed")
        self.assertEqual(
            result,
            {
                "status": "codex_failed",
                "canonical_status": "failed",
                "terminal": True,
                "failure_code": "codex_failed",
            },
        )

    def test_blocked_family_is_terminal(self) -> None:
        self.assertEqual(canonical_status("blocked_result_schema_invalid"), "blocked")
        self.assertTrue(is_terminal_status("blocked_result_schema_invalid"))

    def test_active_states_are_not_terminal(self) -> None:
        for status in ["accepted", "validated", "queued", "claimed", "planning", "executing"]:
            with self.subTest(status=status):
                self.assertFalse(is_terminal_status(status))

    def test_completed_and_preflight_failed_are_terminal(self) -> None:
        self.assertTrue(is_terminal_status("completed"))
        self.assertTrue(is_terminal_status("preflight_failed"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
