import unittest

from scripts.dev_employee_web_console_v2 import page


class WebConsoleV2Tests(unittest.TestCase):
    def test_page_contains_cancel_and_retry_controls(self) -> None:
        content = page()
        self.assertIn("Cancel task", content)
        self.assertIn("Retry terminal task", content)
        self.assertIn("async function cancelGoal()", content)
        self.assertIn("async function retryGoal()", content)
        self.assertIn("/cancel", content)
        self.assertIn("/retry", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
