#!/usr/bin/env python3
"""Persistent conversation/session store for the ORIS Dev Employee Web layer.

The store is deliberately small and filesystem-backed for the current single-host
commercial phase. It uses per-session advisory locks and atomic JSON replacement.
All writes are structured so the implementation can later move to a database
without changing the chat API contract.
"""

from __future__ import annotations

import fcntl
import json
import os
import secrets
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_ROOT = Path("/home/admin/projects/oris/orchestration/dev_employee_chat_sessions")
DEFAULT_LOCK_ROOT = Path("/home/admin/projects/oris/run/dev_employee_chat_locks")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_session_id() -> str:
    return f"chat-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(6)}"


def new_message_id() -> str:
    return f"msg-{secrets.token_hex(10)}"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ChatSessionStore:
    def __init__(self, root: Path = DEFAULT_ROOT, lock_root: Path = DEFAULT_LOCK_ROOT) -> None:
        self.root = Path(root)
        self.lock_root = Path(lock_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock_root.mkdir(parents=True, exist_ok=True)

    def path(self, session_id: str) -> Path:
        if not session_id.startswith("chat-") or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in session_id):
            raise ValueError("invalid session_id")
        return self.root / f"{session_id}.json"

    @contextmanager
    def lock(self, session_id: str) -> Iterator[None]:
        lock_path = self.lock_root / f"{session_id}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def create(self, *, actor: str = "web-user", locale: str = "zh-CN") -> dict[str, Any]:
        session_id = new_session_id()
        timestamp = now_iso()
        session = {
            "session_id": session_id,
            "actor": actor,
            "locale": locale,
            "created_at": timestamp,
            "updated_at": timestamp,
            "selected_project": None,
            "current_task_id": None,
            "task_lineage": [],
            "pending_confirmation": None,
            "provider": None,
            "csrf_token": secrets.token_urlsafe(32),
            "messages": [
                {
                    "message_id": new_message_id(),
                    "role": "assistant",
                    "type": "message",
                    "content": "你好，我是 ORIS AI 开发员工。直接告诉我你希望哪个项目完成什么开发任务，我会自行规划、测试并交付。",
                    "created_at": timestamp,
                }
            ],
        }
        atomic_write_json(self.path(session_id), session)
        return session

    def read(self, session_id: str) -> dict[str, Any]:
        path = self.path(session_id)
        if not path.exists():
            raise FileNotFoundError(session_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, session: dict[str, Any]) -> dict[str, Any]:
        session_id = str(session.get("session_id") or "")
        session["updated_at"] = now_iso()
        atomic_write_json(self.path(session_id), session)
        return session

    def append_message(
        self,
        session: dict[str, Any],
        *,
        role: str,
        content: str,
        message_type: str = "message",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message = {
            "message_id": new_message_id(),
            "role": role,
            "type": message_type,
            "content": content,
            "created_at": now_iso(),
        }
        if metadata:
            message["metadata"] = metadata
        messages = session.setdefault("messages", [])
        messages.append(message)
        return message

    def mutate(self, session_id: str, callback: Any) -> dict[str, Any]:
        with self.lock(session_id):
            session = self.read(session_id)
            callback(session)
            return self.save(session)

    def public_view(self, session: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in session.items()
            if key not in {"csrf_token"}
        }


DEFAULT_CHAT_STORE = ChatSessionStore()
