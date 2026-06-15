import unittest

from scripts.dev_employee_web_console_v3 import chat_page


class WebConsoleV3Tests(unittest.TestCase):
    def test_default_page_is_conversation_first(self) -> None:
        content = chat_page()
        self.assertIn("ORIS AI 开发员工", content)
        self.assertIn("OpenClaw 对话编排", content)
        self.assertIn("textarea", content)
        self.assertIn("/api/chat/bootstrap", content)
        self.assertIn("/api/chat/messages", content)
        self.assertIn("工程管理台", content)

    def test_default_page_hides_engineering_form_fields(self) -> None:
        content = chat_page()
        self.assertNotIn("Console API Token", content)
        self.assertNotIn("Expected checks", content)
        self.assertNotIn("Commit message optional", content)
        self.assertNotIn("lookup_task_id", content)
        self.assertNotIn("Submit goal", content)

    def test_task_card_keeps_technical_details_collapsed(self) -> None:
        content = chat_page()
        self.assertIn("技术详情", content)
        self.assertIn("<details>", content)
        self.assertIn("停止任务", content)
        self.assertIn("重试", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
