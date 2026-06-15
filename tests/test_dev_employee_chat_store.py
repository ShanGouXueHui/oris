import tempfile
import unittest
from pathlib import Path

from scripts.dev_employee_chat_store import ChatSessionStore


class ChatSessionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.store = ChatSessionStore(root / "sessions", root / "locks")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_append_and_public_view(self) -> None:
        session = self.store.create(actor="tester", locale="zh-CN")
        self.assertTrue(session["session_id"].startswith("chat-"))
        self.assertTrue(session["csrf_token"])
        self.assertEqual(session["messages"][0]["role"], "assistant")

        self.store.append_message(session, role="user", content="测试消息")
        saved = self.store.save(session)
        loaded = self.store.read(saved["session_id"])
        self.assertEqual(loaded["messages"][-1]["content"], "测试消息")
        self.assertNotIn("csrf_token", self.store.public_view(loaded))

    def test_mutate_serializes_session_update(self) -> None:
        session = self.store.create()

        def update(payload):
            payload["selected_project"] = "demo"
            self.store.append_message(payload, role="assistant", content="已选择项目")

        updated = self.store.mutate(session["session_id"], update)
        self.assertEqual(updated["selected_project"], "demo")
        self.assertEqual(updated["messages"][-1]["content"], "已选择项目")

    def test_rejects_invalid_session_id(self) -> None:
        with self.assertRaises(ValueError):
            self.store.path("../../etc/passwd")


if __name__ == "__main__":
    unittest.main(verbosity=2)
