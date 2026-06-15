#!/usr/bin/env python3
"""OpenClaw provider boundary for conversational ORIS task orchestration.

The normal provider uses the installed first-party OpenClaw CLI:

    openclaw infer model run --gateway --prompt ... --json

This is a raw model inference path through the running Gateway. It does not load
agent tools, MCP servers, product workspaces, or the Codex executor. The provider
only converts conversation into a validated structured intent. Explicit control
commands remain deterministic and the ORIS intake/control plane remains the sole
owner of task creation, cancellation, retry, and execution.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

ALLOWED_INTENTS = {"create_task", "status", "cancel", "retry", "clarify", "help", "chat"}


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


def compact_project_context(projects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        key: {
            "name": value.get("name"),
            "type": value.get("type"),
            "notes": value.get("notes"),
            "allowed_scope": value.get("allowed_scope", []),
            "forbidden_scope": value.get("forbidden_scope", []),
        }
        for key, value in projects.items()
    }


def compact_recent_messages(session: dict[str, Any], limit: int = 10) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in (session.get("messages") or [])[-limit:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            result.append({"role": role, "content": content[:4000]})
    return result


def safe_current_task(current_task: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(current_task, dict):
        return None
    return {
        "task_id": current_task.get("task_id"),
        "status": current_task.get("status"),
        "canonical_status": current_task.get("canonical_status"),
        "terminal": current_task.get("terminal"),
        "failure_code": current_task.get("failure_code"),
    }


def build_router_prompt(
    *,
    session: dict[str, Any],
    user_message: str,
    projects: dict[str, dict[str, Any]],
    current_task: dict[str, Any] | None,
) -> str:
    context = {
        "locale": session.get("locale") or "zh-CN",
        "selected_project": session.get("selected_project"),
        "current_task_id": session.get("current_task_id"),
        "recent_messages": compact_recent_messages(session),
        "user_message": user_message,
        "available_projects": compact_project_context(projects),
        "current_task": safe_current_task(current_task),
    }
    schema = {
        "intent": "create_task|status|cancel|retry|clarify|help|chat",
        "assistant_message": "concise plain-language response in the user's language",
        "project_key": "one exact available project key or null",
        "objective": "specific engineering objective or null",
        "constraints": ["derived non-secret engineering constraints"],
        "expected_checks": ["relevant check commands only when confidently known"],
        "commit_message": "optional concise commit message or null",
        "requires_confirmation": False,
        "confirmation_reason": "production_change|destructive_change|secret_operation|billing_operation|null",
    }
    return (
        "You are the intent-routing layer for ORIS, an AI development employee.\n"
        "Your only job is to convert the supplied conversation context into one structured response.\n"
        "Do not execute tools, do not edit files, do not run commands, and do not invent project keys.\n"
        "Routine implementation decisions should not be delegated back to the user.\n"
        "Ask a clarification only when the target project or engineering outcome is genuinely ambiguous.\n"
        "Set requires_confirmation=true for production changes, destructive/irreversible operations, secret handling, billing, or purchases.\n"
        "For create_task, preserve the user's real objective and select exactly one available project.\n"
        "Return exactly one JSON object, with no markdown fence and no text before or after it.\n"
        f"Required schema example: {json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}\n"
        f"Conversation context: {json.dumps(context, ensure_ascii=False, separators=(',', ':'))}"
    )


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        preferred = ["text", "content", "output", "response", "completion", "message"]
        seen: set[str] = set()
        for key in preferred:
            if key in value:
                seen.add(key)
                yield from iter_strings(value[key])
        for key, child in value.items():
            if key not in seen:
                yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def parse_json_object_text(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    attempts = [candidate]
    first = candidate.find("{")
    last = candidate.rfind("}")
    if first >= 0 and last > first:
        attempts.append(candidate[first : last + 1])
    for item in attempts:
        try:
            parsed = json.loads(item)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "intent" in parsed:
            return parsed
    return None


def extract_router_result(envelope: dict[str, Any]) -> dict[str, Any]:
    direct = envelope.get("result")
    if isinstance(direct, dict) and "intent" in direct:
        return direct
    for text in iter_strings(envelope):
        parsed = parse_json_object_text(text)
        if parsed is not None:
            return parsed
    raise ProviderContractError("OpenClaw output did not contain the structured intent object")


def validate_provider_result(data: dict[str, Any], projects: dict[str, dict[str, Any]]) -> ProviderResult:
    intent = str(data.get("intent") or "").strip()
    if intent not in ALLOWED_INTENTS:
        raise ProviderContractError(f"unsupported OpenClaw intent: {intent}")
    assistant_message = str(data.get("assistant_message") or "").strip()
    if not assistant_message:
        raise ProviderContractError("OpenClaw response missing assistant_message")
    project_key = str(data.get("project_key") or "").strip() or None
    if project_key and project_key not in projects:
        raise ProviderContractError(f"OpenClaw selected unsupported project: {project_key}")
    objective = str(data.get("objective") or "").strip() or None
    if intent == "create_task" and (not project_key or not objective):
        raise ProviderContractError("create_task requires project_key and objective")
    constraints = [str(item).strip() for item in data.get("constraints") or [] if str(item).strip()]
    checks = [str(item).strip() for item in data.get("expected_checks") or [] if str(item).strip()]
    return ProviderResult(
        intent=intent,
        assistant_message=assistant_message,
        project_key=project_key,
        objective=objective,
        constraints=constraints[:30],
        expected_checks=checks[:30],
        commit_message=str(data.get("commit_message") or "").strip() or None,
        requires_confirmation=bool(data.get("requires_confirmation")),
        confirmation_reason=str(data.get("confirmation_reason") or "").strip() or None,
        provider="openclaw_infer_gateway",
    )


class OpenClawInferCLIProvider:
    def __init__(
        self,
        binary: Path,
        *,
        timeout: int = 90,
        model: str | None = None,
        thinking: str = "low",
        require_gateway: bool = True,
    ) -> None:
        self.binary = Path(binary)
        self.timeout = timeout
        self.model = model
        self.thinking = thinking
        self.require_gateway = require_gateway

    def command(self, prompt: str) -> list[str]:
        command = [
            str(self.binary),
            "infer",
            "model",
            "run",
            "--gateway",
            "--prompt",
            prompt,
            "--thinking",
            self.thinking,
            "--json",
        ]
        if self.model:
            command.extend(["--model", self.model])
        return command

    def analyze(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
        projects: dict[str, dict[str, Any]],
        current_task: dict[str, Any] | None,
    ) -> ProviderResult:
        if not self.binary.is_file() or not os.access(self.binary, os.X_OK):
            raise ProviderUnavailable("OpenClaw binary is unavailable")
        prompt = build_router_prompt(
            session=session,
            user_message=user_message,
            projects=projects,
            current_task=current_task,
        )
        try:
            completed = subprocess.run(
                self.command(prompt),
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderUnavailable("OpenClaw inference timed out") from exc
        if completed.returncode != 0:
            raise ProviderUnavailable(f"OpenClaw inference exited with code {completed.returncode}")
        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderContractError("OpenClaw CLI returned invalid JSON envelope") from exc
        if not isinstance(envelope, dict):
            raise ProviderContractError("OpenClaw CLI envelope must be an object")
        if envelope.get("ok") is False:
            raise ProviderUnavailable("OpenClaw inference envelope reported failure")
        transport = str(envelope.get("transport") or (envelope.get("meta") or {}).get("transport") or "").strip()
        if self.require_gateway and transport and transport != "gateway":
            raise ProviderUnavailable(f"OpenClaw transport is not gateway: {transport}")
        data = extract_router_result(envelope)
        result = validate_provider_result(data, projects)
        result.raw_metadata = {
            "transport": transport or "gateway_requested",
            "provider": envelope.get("provider"),
            "model": envelope.get("model"),
            "capability": envelope.get("capability"),
            "openclaw_binary": str(self.binary),
        }
        return result


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
            return ProviderResult(intent="clarify", assistant_message=f"请告诉我要操作哪个项目。当前可用项目：{choices}")
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


def explicit_control_intent(text: str) -> bool:
    lowered = text.lower()
    provider = DeterministicFallbackProvider()
    groups = [provider.STATUS_WORDS, provider.CANCEL_WORDS, provider.RETRY_WORDS, provider.HELP_WORDS]
    return any(word in lowered for group in groups for word in group)


def configured_provider() -> OpenClawInferCLIProvider | None:
    binary_value = os.environ.get("ORIS_OPENCLAW_BIN", "/home/admin/.npm-global/bin/openclaw").strip()
    binary = Path(binary_value).expanduser()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        return None
    timeout = max(10, min(180, int(os.environ.get("ORIS_OPENCLAW_TIMEOUT_SECONDS", "90"))))
    model = os.environ.get("ORIS_OPENCLAW_MODEL", "").strip() or None
    thinking = os.environ.get("ORIS_OPENCLAW_THINKING", "low").strip() or "low"
    require_gateway = os.environ.get("ORIS_OPENCLAW_REQUIRE_GATEWAY", "1").strip().lower() not in {"0", "false", "no"}
    return OpenClawInferCLIProvider(
        binary,
        timeout=timeout,
        model=model,
        thinking=thinking,
        require_gateway=require_gateway,
    )


def merge_mandatory_policy(result: ProviderResult, user_message: str, projects: dict[str, dict[str, Any]]) -> ProviderResult:
    fallback = DeterministicFallbackProvider()
    risk = fallback.is_risky(user_message)
    if risk:
        result.requires_confirmation = True
        result.confirmation_reason = risk
        if result.intent == "create_task":
            result.intent = "clarify"
        result.assistant_message = "这个请求涉及生产、敏感信息、付费或不可逆操作，需要你明确确认操作范围后才能继续。"
    if result.intent == "create_task" and result.project_key in projects:
        mandatory = fallback.default_constraints(projects[result.project_key])
        merged: list[str] = []
        for item in [*mandatory, *result.constraints]:
            if item and item not in merged:
                merged.append(item)
        result.constraints = merged[:30]
    return result


def analyze_message(
    *,
    session: dict[str, Any],
    user_message: str,
    projects: dict[str, dict[str, Any]],
    current_task: dict[str, Any] | None,
) -> ProviderResult:
    fallback = DeterministicFallbackProvider()
    if explicit_control_intent(user_message):
        return fallback.analyze(
            session=session,
            user_message=user_message,
            projects=projects,
            current_task=current_task,
        )

    provider = configured_provider()
    if provider is not None:
        try:
            result = provider.analyze(
                session=session,
                user_message=user_message,
                projects=projects,
                current_task=current_task,
            )
            return merge_mandatory_policy(result, user_message, projects)
        except (ProviderUnavailable, ProviderContractError) as exc:
            result = fallback.analyze(
                session=session,
                user_message=user_message,
                projects=projects,
                current_task=current_task,
            )
            result.raw_metadata = {
                "openclaw_fallback": True,
                "fallback_reason": type(exc).__name__,
            }
            return result
    return fallback.analyze(
        session=session,
        user_message=user_message,
        projects=projects,
        current_task=current_task,
    )
