import unittest

from scripts.dev_employee_task_states import (
    can_transition,
    canonical_status,
    classify,
    is_active_status,
    is_terminal_status,
)


class TaskStateTests(unittest.TestCase):
    def test_legacy_codex_failed_is_terminal_failed(self) -> None:
        result = classify("codex_failed")
        self.assertEqual(
            result,
            {
                "status": "codex_failed",
                "canonical_status": "failed",
                "active": False,
                "terminal": True,
                "failure_code": "codex_failed",
            },
        )

    def test_runtime_states_map_to_canonical_active_states(self) -> None:
        expected = {
            "running": "claimed",
            "preflight": "claimed",
            "codex_running": "executing",
            "cancel_requested": "cancelling",
        }
        for raw, canonical in expected.items():
            with self.subTest(raw=raw):
                self.assertEqual(canonical_status(raw), canonical)
                self.assertTrue(is_active_status(raw))
                self.assertFalse(is_terminal_status(raw))

    def test_blocked_family_is_terminal(self) -> None:
        self.assertEqual(canonical_status("blocked_result_schema_invalid"), "blocked")
        self.assertTrue(is_terminal_status("blocked_result_schema_invalid"))

    def test_active_states_are_not_terminal(self) -> None:
        for status in [
            "accepted",
            "validated",
            "queued",
            "claimed",
            "planning",
            "executing",
            "local_checks_passed",
            "committing",
            "pushing",
            "cancelling",
        ]:
            with self.subTest(status=status):
                self.assertTrue(is_active_status(status))
                self.assertFalse(is_terminal_status(status))

    def test_canonical_failure_stages_remain_distinct_and_terminal(self) -> None:
        for status in ["preflight_failed", "local_checks_failed", "remote_verification_failed"]:
            with self.subTest(status=status):
                self.assertEqual(canonical_status(status), status)
                self.assertTrue(is_terminal_status(status))

    def test_completed_is_terminal(self) -> None:
        self.assertEqual(canonical_status("completed"), "completed")
        self.assertTrue(is_terminal_status("completed"))

    def test_transition_policy_allows_happy_path_and_rejects_terminal_restart(self) -> None:
        happy_path = [
            ("accepted", "validated"),
            ("validated", "queued"),
            ("queued", "claimed"),
            ("claimed", "executing"),
            ("executing", "local_checks_passed"),
            ("local_checks_passed", "committing"),
            ("committing", "pushing"),
            ("pushing", "completed"),
        ]
        for source, target in happy_path:
            with self.subTest(source=source, target=target):
                self.assertTrue(can_transition(source, target))
        self.assertFalse(can_transition("completed", "queued"))
        self.assertFalse(can_transition("cancelled", "executing"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
