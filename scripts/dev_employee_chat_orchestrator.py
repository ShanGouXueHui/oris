#!/usr/bin/env python3
"""Conversation-to-task orchestration for the ORIS Dev Employee Web layer.

This module translates natural-language conversation into the existing intake
control plane. It does not mutate queue files, run Codex, edit products, or push
Git directly. The authoritative lifecycle remains intake v2 + queue kernel.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import dev_employee_web_console as web_base
from dev_employee_chat_store import DEFAULT_CHAT_STORE, ChatSessionStore
from dev_employee_openclaw_provider import ProviderResult, analyze_message

REGISTRY_PATH = Path("/home/admin/projects/oris/orchestration/project_registry.json")

PLAIN_STATUS = {
    "accepted": "正在接收任务",
    "validated": "正在准备",
    "queued": "等待开始",
    "claimed": "正在规划",
    "planning": "正在规划",
    "executing": "正在开发",
    "local_checks_passed": "测试已通过",
    "committing": "正在整理提交",
    "pushing": "正在交付",
    "completed": "已完成",
    "cancelling": "正在安全停止",
    "cancelled": "已停止",
    "preflight_failed": "启动检查未通过",
    "local_checks_failed": "测试未通过",
    "remote_verification_failed": "交付验证未通过",
    "blocked": "需要处理",
    "failed": "执行失败",
    "error": "发生错误",
}

CONFIRM_WORDS = {"确认", "确认执行", "继续", "同意", "yes", "confirm", "proceed"}
DECLINE_WORDS = {"取消", "不执行", "不用了", "no", "cancel"}


def registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def allowed_projects() -> dict[str, dict[str, Any]]:
    all_projects = registry().get("projects", {})
    allowed = web_base.allowed_projects()
    return {
        key: {
            "project_key": key,
            "name": value.get("name", key),
            "type": value.get("type"),
            "product_path": value.get("local_path"),
            "product_repo": str(value.get("repo") or "").removeprefix("git@github.com:").removesuffix(".git"),
            "default_branch": value.get("default_branch", "main"),
            "allowed_scope": value.get("allowed_scope", []),
            "forbidden_scope": value.get("forbidden_scope", []),
            "notes": value.get("notes", ""),
        }
        for key, value in all_projects.items()
        if key in allowed
    }


def intake(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    status, payload = web_base.intake_request(method, path, body=body, auth=method != "GET")
    if not isinstance(payload, dict):
        return status, {"raw": payload}
    return status, payload


def current_task_status(session: dict[str, Any]) -> dict[str, Any] | None:
    task_id = str(session.get("current_task_id") or "")
    if not task_id:
        return None
    status, payload = intake("GET", f"/goals/{task_id}")
    if status == 404:
        return None
    if status < 200 or status >= 300:
        return {
            "task_id": task_id,
            "status": "error",
            "canonical_status": "error",
            "terminal": True,
            "failure_code": f"status_http_{status}",
        }
    return payload


def plain_status(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "尚未开始"
    canonical = str(payload.get("canonical_status") or payload.get("status") or "unknown")
    return PLAIN_STATUS.get(canonical, "处理中")


def task_card(payload: dict[str, Any], projects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    catalog = payload.get("catalog") if isinstance(payload.get("catalog"), dict) else {}
    project_key = str(catalog.get("project_key") or payload.get("project_key") or "")
    project = projects.get(project_key, {})
    canonical = str(payload.get("canonical_status") or payload.get("status") or "unknown")
    terminal = bool(payload.get("terminal"))
    technical = {
        "task_id": payload.get("task_id"),
        "status": payload.get("status"),
        "canonical_status": canonical,
        "failure_code": payload.get("failure_code"),
        "attempt": (payload.get("idempotency") or {}).get("attempt") if isinstance(payload.get("idempotency"), dict) else catalog.get("attempt"),
        "max_attempts": (payload.get("idempotency") or {}).get("max_attempts") if isinstance(payload.get("idempotency"), dict) else catalog.get("max_attempts"),
        "product_commit_sha": (payload.get("github_evidence") or {}).get("product_commit_sha") if isinstance(payload.get("github_evidence"), dict) else None,
        "product_remote_sha": (payload.get("github_evidence") or {}).get("product_remote_sha") if isinstance(payload.get("github_evidence"), dict) else None,
        "oris_evidence_commit_sha": (payload.get("github_evidence") or {}).get("oris_evidence_commit_sha") if isinstance(payload.get("github_evidence"), dict) else None,
    }
    actions: list[str] = []
    if not terminal and canonical not in {"committing", "pushing"}:
        actions.append("cancel")
    if terminal and canonical != "completed":
        actions.append("retry")
    actions.append("refresh")
    return {
        "task_id": payload.get("task_id"),
        "project_key": project_key or None,
        "project_name": project.get("name") or project_key or "当前项目",
        "plain_status": plain_status(payload),
        "canonical_status": canonical,
        "terminal": terminal,
        "actions": actions,
        "technical": technical,
    }


def build_task_id(project_key: str, session_id: str) -> str:
    safe_project = re.sub(r"[^A-Za-z0-9_-]+", "-", project_key).strip("-")[:50]
    session_suffix = session_id.rsplit("-", 1)[-1][:12]
    return f"chat-{safe_project}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{session_suffix}"


def task_payload(result: ProviderResult, session: dict[str, Any], projects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not result.project_key or result.project_key not in projects:
        raise ValueError("provider did not select a valid project")
    if not result.objective:
        raise ValueError("provider did not produce an objective")
    project = projects[result.project_key]
    task_id = build_task_id(result.project_key, str(session["session_id"]))
    commit_message = result.commit_message or f"feat(dev-employee): complete conversational task {task_id}"
    return {
        "task_id": task_id,
        "project_key": result.project_key,
        "objective": result.objective,
        "constraints": result.constraints,
        "expected_checks": result.expected_checks,
        "commit_message": commit_message,
        "notes": [
            f"Created from conversational session {session['session_id']}.",
            f"Conversation provider: {result.provider}.",
            f"Project policy: {project.get('notes', '')}",
        ],
        "max_attempts": 3,
        "lease_seconds": 60,
        "execution_timeout_seconds": 7200,
    }


def append_task_card(store: ChatSessionStore, session: dict[str, Any], payload: dict[str, Any], projects: dict[str, dict[str, Any]]) -> None:
    card = task_card(payload, projects)
    store.append_message(
        session,
        role="assistant",
        message_type="task_card",
        content=f"{card['project_name']} · {card['plain_status']}",
        metadata=card,
    )


def handle_confirmation(
    store: ChatSessionStore,
    session: dict[str, Any],
    user_message: str,
    projects: dict[str, dict[str, Any]],
) -> bool:
    pending = session.get("pending_confirmation")
    if not isinstance(pending, dict):
        return False
    normalized = user_message.strip().lower()
    if normalized in DECLINE_WORDS:
        session["pending_confirmation"] = None
        store.append_message(session, role="assistant", content="已取消，本次高风险操作不会执行。")
        return True
    if normalized not in CONFIRM_WORDS:
        store.append_message(
            session,
            role="assistant",
            content="该请求仍在等待明确确认。回复“确认执行”继续，或回复“取消”。",
        )
        return True
    result = ProviderResult(**pending["provider_result"])
    result.requires_confirmation = False
    result.confirmation_reason = None
    session["pending_confirmation"] = None
    create_task_from_result(store, session, result, projects)
    return True


def create_task_from_result(
    store: ChatSessionStore,
    session: dict[str, Any],
    result: ProviderResult,
    projects: dict[str, dict[str, Any]],
) -> None:
    existing = current_task_status(session)
    if existing and not existing.get("terminal"):
        store.append_message(
            session,
            role="assistant",
            content="当前会话已有任务正在处理。我先继续跟踪它；完成或停止后再创建新任务。",
        )
        append_task_card(store, session, existing, projects)
        return
    payload = task_payload(result, session, projects)
    status_code, created = intake("POST", "/goals", payload)
    if status_code not in {200, 201}:
        message = str(created.get("message") or created.get("error") or f"HTTP {status_code}")
        store.append_message(session, role="assistant", content=f"任务暂时没有成功创建：{message}")
        return
    session["selected_project"] = result.project_key
    session["current_task_id"] = created.get("task_id") or payload["task_id"]
    session["provider"] = result.provider
    lineage = session.setdefault("task_lineage", [])
    if session["current_task_id"] not in lineage:
        lineage.append(session["current_task_id"])
    store.append_message(session, role="assistant", content=result.assistant_message)
    current = created.get("current_status") if isinstance(created.get("current_status"), dict) else None
    if current is None:
        _, current = intake("GET", f"/goals/{session['current_task_id']}")
    append_task_card(store, session, current, projects)


def process_message(
    session_id: str,
    user_message: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_STORE,
) -> dict[str, Any]:
    text = user_message.strip()
    if not text:
        raise ValueError("message is required")
    if len(text) > 12_000:
        raise ValueError("message is too long")
    projects = allowed_projects()
    if not projects:
        raise RuntimeError("no conversational project is allowed")

    with store.lock(session_id):
        session = store.read(session_id)
        store.append_message(session, role="user", content=text)
        if handle_confirmation(store, session, text, projects):
            return store.public_view(store.save(session))

        current = current_task_status(session)
        result = analyze_message(
            session=session,
            user_message=text,
            projects=projects,
            current_task=current,
        )
        session["provider"] = result.provider

        if result.requires_confirmation:
            session["pending_confirmation"] = {
                "provider_result": result.to_dict(),
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            store.append_message(
                session,
                role="assistant",
                message_type="confirmation_request",
                content=result.assistant_message + " 回复“确认执行”继续，或回复“取消”。",
                metadata={"reason": result.confirmation_reason},
            )
        elif result.intent == "create_task":
            create_task_from_result(store, session, result, projects)
        elif result.intent == "status":
            current = current_task_status(session)
            if current:
                store.append_message(session, role="assistant", content=f"当前任务状态：{plain_status(current)}。")
                append_task_card(store, session, current, projects)
            else:
                store.append_message(session, role="assistant", content="当前会话还没有任务。")
        elif result.intent == "cancel":
            task_id = str(session.get("current_task_id") or "")
            if not task_id:
                store.append_message(session, role="assistant", content="当前没有可停止的任务。")
            else:
                status_code, payload = intake(
                    "POST",
                    f"/goals/{task_id}/cancel",
                    {"reason": "Conversation user requested cancellation", "requested_by": "openclaw-chat"},
                )
                if status_code not in {200, 202}:
                    store.append_message(session, role="assistant", content=f"当前无法停止任务：{payload.get('message') or payload.get('error') or status_code}")
                else:
                    current = payload.get("current_status") if isinstance(payload.get("current_status"), dict) else payload
                    store.append_message(session, role="assistant", content="已提交安全停止请求。")
                    append_task_card(store, session, current, projects)
        elif result.intent == "retry":
            task_id = str(session.get("current_task_id") or "")
            if not task_id:
                store.append_message(session, role="assistant", content="当前没有可重试的任务。")
            else:
                status_code, payload = intake(
                    "POST",
                    f"/goals/{task_id}/retry",
                    {"reason": "Conversation user requested retry", "requested_by": "openclaw-chat"},
                )
                if status_code not in {200, 201}:
                    store.append_message(session, role="assistant", content=f"当前无法重试：{payload.get('message') or payload.get('error') or status_code}")
                else:
                    retry_id = str(payload.get("task_id") or "")
                    if retry_id:
                        session["current_task_id"] = retry_id
                        lineage = session.setdefault("task_lineage", [])
                        if retry_id not in lineage:
                            lineage.append(retry_id)
                    store.append_message(session, role="assistant", content="已创建显式重试，我会继续跟踪新的任务。")
                    current = payload.get("current_status") if isinstance(payload.get("current_status"), dict) else None
                    if current is None and retry_id:
                        _, current = intake("GET", f"/goals/{retry_id}")
                    if current:
                        append_task_card(store, session, current, projects)
        else:
            store.append_message(session, role="assistant", content=result.assistant_message)

        return store.public_view(store.save(session))


def refresh_session(
    session_id: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_STORE,
    append_if_changed: bool = False,
) -> dict[str, Any]:
    projects = allowed_projects()
    with store.lock(session_id):
        session = store.read(session_id)
        current = current_task_status(session)
        if current:
            card = task_card(current, projects)
            session["current_task_snapshot"] = card
            if append_if_changed:
                previous = None
                for message in reversed(session.get("messages") or []):
                    if message.get("type") == "task_card":
                        previous = (message.get("metadata") or {}).get("canonical_status")
                        break
                if previous != card["canonical_status"]:
                    store.append_message(
                        session,
                        role="assistant",
                        content=f"任务状态已更新：{card['plain_status']}。",
                    )
                    append_task_card(store, session, current, projects)
        return store.public_view(store.save(session))
