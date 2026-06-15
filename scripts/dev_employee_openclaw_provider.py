#!/usr/bin/env python3
"""OpenClaw provider boundary for conversational ORIS task orchestration.

The Web layer depends on this structured interface rather than a specific model
or OpenClaw deployment. A configured HTTP provider is preferred. A deterministic
fallback remains available for safe status/cancel/retry commands and for direct
single-project engineering goals when the provider is unavailable.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProviderResult:
    intent: str
    assistant_message: str
    project_key: str | None = None
    objective: str | None = None
    constraints: list[str] = field(default_factory=list)
    expected_checks: list[str] = field(default_factory=list)
    commit_message: str | None = None
    requires_confirmation: bool = False
    confirmation_reason: str | None = None
    provider: str = "deterministic_fallback"
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProviderUnavailable(RuntimeError):
    pass


class ProviderContractError(RuntimeError):
    pass


class OpenClawHTTPProvider:
    def __init__(self, endpoint: str, token_file: Path | None = None, timeout: int = 45) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.token_file = token_file
        self.timeout = timeout

    def token(self) -> str:
        if self.token_file is None:
            return ""
        try:
            return self.token_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""

    def analyze(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
        projects: dict[str, dict[str, Any]],
        current_task: dict[str, Any] | None,
    ) -> ProviderResult:
        payload = {
            "contract_version": 1,
            "session": {
                "session_id": session.get("session_id"),
                "locale": session.get("locale"),
                "selected_project": session.get("selected_project"),
                "current_task_id": session.get("current_task_id"),
                "recent_messages": (session.get("messages") or [])[-12:],
            },
            "user_message": user_message,
            "projects": {
                key: {
                    "name": value.get("name"),
                    "type": value.get("type"),
                    "notes": value.get("notes"),
                    "allowed_scope": value.get("allowed_scope", []),
                    "forbidden_scope": value.get("forbidden_scope", []),
                }
                for key, value in projects.items()
            },
            "current_task": current_task,
            "response_schema": {
                "intent": "create_task|status|cancel|retry|clarify|help|chat",
                "assistant_message": "plain-language response",
                "project_key": "optional project key",
                "objective": "optional structured engineering objective",
                "constraints": ["optional constraints"],
                "expected_checks": ["optional checks"],
                "commit_message": "optional commit message",
                "requires_confirmation": False,
                "confirmation_reason": "optional",
            },
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        token = self.token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                if response.status < 200 or response.status >= 300:
                    raise ProviderUnavailable(f"OpenClaw provider returned HTTP {response.status}")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderUnavailable(f"OpenClaw provider unavailable: {type(exc).__name__}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderContractError("OpenClaw provider returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise ProviderContractError("OpenClaw provider response must be an object")
        intent = str(data.get("intent") or "").strip()
        assistant_message = str(data.get("assistant_message") or "").strip()
        if intent not in {"create_task", "status", "cancel", "retry", "clarify", "help", "chat"}:
            raise ProviderContractError(f"unsupported OpenClaw intent: {intent}")
        if not assistant_message:
            raise ProviderContractError("OpenClaw response missing assistant_message")
        project_key = str(data.get("project_key") or "").strip() or None
        if project_key and project_key not in projects:
            raise ProviderContractError(f"OpenClaw selected unsupported project: {project_key}")
        return ProviderResult(
            intent=intent,
            assistant_message=assistant_message,
            project_key=project_key,
            objective=str(data.get("objective") or "").strip() or None,
            constraints=[str(item).strip() for item in data.get("constraints") or [] if str(item).strip()],
            expected_checks=[str(item).strip() for item in data.get("expected_checks") or [] if str(item).strip()],
            commit_message=str(data.get("commit_message") or "").strip() or None,
            requires_confirmation=bool(data.get("requires_confirmation")),
            confirmation_reason=str(data.get("confirmation_reason") or "").strip() or None,
            provider="openclaw_http",
            raw_metadata={
                "endpoint_configured": True,
                "contract_version": data.get("contract_version", 1),
            },
        )


class DeterministicFallbackProvider:
    STATUS_WORDS = ("进度", "状态", "怎么样了", "完成了吗", "status", "progress", "how is")
    CANCEL_WORDS = ("停止任务", "取消任务", "停掉", "停止", "取消", "stop task", "cancel task")
    RETRY_WORDS = ("重试", "再试一次", "重新执行", "retry", "try again")
    HELP_WORDS = ("帮助", "怎么用", "help", "what can you do")

    def infer_project(self, text: str, projects: dict[str, dict[str, Any]], selected: str | None) -> str | None:
        lowered = text.lower()
        matches: list[str] = []
        for key, project in projects.items():
            names = [key, str(project.get("name") or "")]
            if any(name and name.lower() in lowered for name in names):
                matches.append(key)
        if len(matches) == 1:
            return matches[0]
        if selected and selected in projects:
            return selected
        if len(projects) == 1:
            return next(iter(projects))
        return None

    def is_risky(self, text: str) -> str | None:
        lowered = text.lower()
        patterns = {
            "production_change": ("生产环境", "production", "prod ", "上线", "部署到生产"),
            "destructive_change": ("删除数据库", "drop database", "清空数据", "永久删除", "force push"),
            "secret_operation": ("密码", "密钥", "token", "secret", "private key"),
            "billing_operation": ("付款", "付费", "购买", "billing", "purchase"),
        }
        for reason, words in patterns.items():
            if any(word in lowered for word in words):
                return reason
        return None

    def default_constraints(self, project: dict[str, Any]) -> list[str]:
        constraints = [
            "Modify only the selected standalone project repository.",
            "Preserve existing behavior and public contracts unless the objective explicitly requires a change.",
            "Choose routine implementation details autonomously and keep the change minimal.",
            "Run relevant existing tests and add focused coverage for new behavior.",
            "Do not read, print, commit, or expose secrets or production credentials.",
            "Commit and push only after checks pass, then emit structured evidence.",
        ]
        forbidden = [str(item) for item in project.get("forbidden_scope") or []]
        if forbidden:
            constraints.append("Forbidden scope: " + ", ".join(forbidden))
        return constraints

    def analyze(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
        projects: dict[str, dict[str, Any]],
        current_task: dict[str, Any] | None,
    ) -> ProviderResult:
        text = user_message.strip()
        lowered = text.lower()
        if any(word in lowered for word in self.HELP_WORDS):
            return ProviderResult(
                intent="help",
                assistant_message="你可以直接告诉我：哪个项目需要完成什么开发目标。我会自行规划、实现、测试和交付。也可以说“查看进度”“停止任务”或“重试”。",
            )
        if any(word in lowered for word in self.CANCEL_WORDS):
            if not session.get("current_task_id"):
                return ProviderResult(intent="clarify", assistant_message="当前会话没有正在处理的任务。请先告诉我要完成什么开发工作。")
            return ProviderResult(intent="cancel", assistant_message="我会安全停止当前任务，并保留完整审计记录。")
        if any(word in lowered for word in self.RETRY_WORDS):
            if not session.get("current_task_id"):
                return ProviderResult(intent="clarify", assistant_message="当前会话没有可重试的任务。")
            return ProviderResult(intent="retry", assistant_message="我会为当前终态任务创建一次显式重试，并继续在同一会话中跟踪。")
        if any(word in lowered for word in self.STATUS_WORDS):
            if not session.get("current_task_id"):
                return ProviderResult(intent="chat", assistant_message="当前会话还没有任务。直接告诉我需要完成的开发目标即可。")
            return ProviderResult(intent="status", assistant_message="我正在读取当前任务的最新状态。")

        project_key = self.infer_project(text, projects, session.get("selected_project"))
        if not project_key:
            choices = "、".join(f"{key}（{value.get('name', key)}）" for key, value in projects.items())
            return ProviderResult(
                intent="clarify",
                assistant_message=f"请告诉我要操作哪个项目。当前可用项目：{choices}",
            )
        risk = self.is_risky(text)
        if risk:
            return ProviderResult(
                intent="clarify",
                assistant_message="这个请求涉及生产、敏感信息、付费或不可逆操作，需要你明确确认操作范围后才能继续。",
                project_key=project_key,
                objective=text,
                requires_confirmation=True,
                confirmation_reason=risk,
            )
        project = projects[project_key]
        objective = re.sub(r"\s+", " ", text).strip()
        if len(objective) < 12:
            return ProviderResult(
                intent="clarify",
                assistant_message="目标还不够具体。请补充要新增、修复或调整的功能，以及期望结果。",
                project_key=project_key,
            )
        return ProviderResult(
            intent="create_task",
            assistant_message=f"已理解。我会在“{project.get('name', project_key)}”中自行完成规划、开发、测试、提交和证据记录。任务即将开始。",
            project_key=project_key,
            objective=objective,
            constraints=self.default_constraints(project),
            expected_checks=[],
            commit_message=None,
            provider="deterministic_fallback",
        )


def configured_provider() -> OpenClawHTTPProvider | None:
    endpoint = os.environ.get("ORIS_OPENCLAW_CHAT_URL", "").strip()
    if not endpoint:
        return None
    token_file_value = os.environ.get("ORIS_OPENCLAW_TOKEN_FILE", "").strip()
    token_file = Path(token_file_value).expanduser() if token_file_value else None
    timeout = max(5, min(120, int(os.environ.get("ORIS_OPENCLAW_TIMEOUT_SECONDS", "45"))))
    return OpenClawHTTPProvider(endpoint, token_file=token_file, timeout=timeout)


def analyze_message(
    *,
    session: dict[str, Any],
    user_message: str,
    projects: dict[str, dict[str, Any]],
    current_task: dict[str, Any] | None,
) -> ProviderResult:
    provider = configured_provider()
    if provider is not None:
        try:
            return provider.analyze(
                session=session,
                user_message=user_message,
                projects=projects,
                current_task=current_task,
            )
        except (ProviderUnavailable, ProviderContractError) as exc:
            fallback = DeterministicFallbackProvider().analyze(
                session=session,
                user_message=user_message,
                projects=projects,
                current_task=current_task,
            )
            fallback.raw_metadata = {
                "openclaw_fallback": True,
                "fallback_reason": type(exc).__name__,
            }
            return fallback
    return DeterministicFallbackProvider().analyze(
        session=session,
        user_message=user_message,
        projects=projects,
        current_task=current_task,
    )
