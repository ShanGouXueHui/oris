import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.dev_employee_openclaw_provider as provider_module
from scripts.dev_employee_openclaw_provider import (
    DeterministicFallbackProvider,
    OpenClawInferCLIProvider,
    ProviderUnavailable,
    analyze_message,
    extract_router_result,
    validate_provider_result,
)


class OpenClawProviderFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DeterministicFallbackProvider()
        self.projects = {
            "demo": {
                "name": "Demo Project",
                "type": "test_project",
                "forbidden_scope": [".env", "secrets"],
            }
        }
        self.session = {
            "session_id": "chat-test",
            "selected_project": None,
            "current_task_id": None,
            "messages": [],
        }

    def test_single_project_goal_becomes_create_task(self) -> None:
        result = self.provider.analyze(
            session=self.session,
            user_message="给 Demo Project 增加一个 /healthz 接口并完成测试",
            projects=self.projects,
            current_task=None,
        )
        self.assertEqual(result.intent, "create_task")
        self.assertEqual(result.project_key, "demo")
        self.assertIn("/healthz", result.objective)
        self.assertTrue(result.constraints)

    def test_status_cancel_retry_are_deterministic(self) -> None:
        session = {**self.session, "current_task_id": "goal-demo"}
        expectations = {
            "查看进度": "status",
            "停止任务": "cancel",
            "重试": "retry",
        }
        for message, intent in expectations.items():
            with self.subTest(message=message):
                result = self.provider.analyze(
                    session=session,
                    user_message=message,
                    projects=self.projects,
                    current_task={"task_id": "goal-demo"},
                )
                self.assertEqual(result.intent, intent)

    def test_risky_request_requires_confirmation(self) -> None:
        result = self.provider.analyze(
            session=self.session,
            user_message="把 Demo Project 直接部署到生产环境并使用新的 token",
            projects=self.projects,
            current_task=None,
        )
        self.assertEqual(result.intent, "clarify")
        self.assertTrue(result.requires_confirmation)
        self.assertIsNotNone(result.confirmation_reason)

    def test_multiple_projects_without_match_asks_for_clarification(self) -> None:
        projects = {**self.projects, "another": {"name": "Another Project"}}
        result = self.provider.analyze(
            session=self.session,
            user_message="增加一个新的健康检查接口并测试",
            projects=projects,
            current_task=None,
        )
        self.assertEqual(result.intent, "clarify")
        self.assertIn("哪个项目", result.assistant_message)


class OpenClawInferContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projects = {
            "demo": {
                "name": "Demo Project",
                "type": "test_project",
                "forbidden_scope": [".env", "secrets"],
            }
        }
        self.session = {
            "session_id": "chat-test",
            "locale": "zh-CN",
            "selected_project": None,
            "current_task_id": None,
            "messages": [],
        }

    def test_extracts_intent_from_openclaw_outputs_text(self) -> None:
        inner = {
            "intent": "create_task",
            "assistant_message": "已理解。",
            "project_key": "demo",
            "objective": "增加 /healthz 并测试",
            "constraints": [],
            "expected_checks": [],
            "commit_message": None,
            "requires_confirmation": False,
            "confirmation_reason": None,
        }
        envelope = {
            "ok": True,
            "transport": "gateway",
            "provider": "example",
            "model": "example-model",
            "outputs": [{"type": "text", "text": json.dumps(inner, ensure_ascii=False)}],
        }
        extracted = extract_router_result(envelope)
        result = validate_provider_result(extracted, self.projects)
        self.assertEqual(result.intent, "create_task")
        self.assertEqual(result.project_key, "demo")

    def test_extracts_markdown_wrapped_json_defensively(self) -> None:
        envelope = {
            "ok": True,
            "transport": "gateway",
            "outputs": [
                {
                    "text": "```json\n{\"intent\":\"help\",\"assistant_message\":\"可以直接描述任务。\"}\n```"
                }
            ],
        }
        result = validate_provider_result(extract_router_result(envelope), self.projects)
        self.assertEqual(result.intent, "help")

    def test_gateway_requirement_rejects_explicit_local_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "openclaw"
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o700)
            provider = OpenClawInferCLIProvider(binary, require_gateway=True)
            completed = type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {
                            "ok": True,
                            "transport": "local",
                            "outputs": [
                                {
                                    "text": json.dumps(
                                        {
                                            "intent": "help",
                                            "assistant_message": "帮助",
                                        },
                                        ensure_ascii=False,
                                    )
                                }
                            ],
                        }
                    ),
                    "stderr": "",
                },
            )()
            with patch.object(provider_module.subprocess, "run", return_value=completed):
                with self.assertRaises(ProviderUnavailable):
                    provider.analyze(
                        session=self.session,
                        user_message="介绍能力",
                        projects=self.projects,
                        current_task=None,
                    )

    def test_explicit_control_does_not_call_model_provider(self) -> None:
        session = {**self.session, "current_task_id": "goal-demo"}
        with patch.object(provider_module, "configured_provider", side_effect=AssertionError("must not be called")):
            result = analyze_message(
                session=session,
                user_message="停止任务",
                projects=self.projects,
                current_task={"task_id": "goal-demo"},
            )
        self.assertEqual(result.intent, "cancel")
        self.assertEqual(result.provider, "deterministic_fallback")

    def test_mandatory_policy_is_merged_after_model_result(self) -> None:
        fake = type(
            "Provider",
            (),
            {
                "analyze": lambda self, **kwargs: provider_module.ProviderResult(
                    intent="create_task",
                    assistant_message="已理解。",
                    project_key="demo",
                    objective="增加 /healthz 并测试",
                    constraints=["Use a focused implementation."],
                    provider="openclaw_infer_gateway",
                )
            },
        )()
        with patch.object(provider_module, "configured_provider", return_value=fake):
            result = analyze_message(
                session=self.session,
                user_message="给 Demo Project 增加 /healthz 并测试",
                projects=self.projects,
                current_task=None,
            )
        self.assertEqual(result.provider, "openclaw_infer_gateway")
        self.assertTrue(any("selected standalone project" in item for item in result.constraints))
        self.assertIn("Use a focused implementation.", result.constraints)


if __name__ == "__main__":
    unittest.main(verbosity=2)
