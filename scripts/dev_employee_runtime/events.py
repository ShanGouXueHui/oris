from __future__ import annotations

import fcntl
import os
import uuid
from pathlib import Path
from typing import Any

from .audit import privacy_safe_details
from .clock import now_iso
from .json_store import canonical_json


def append_event(
    path: Path,
    *,
    task_id: str,
    event_type: str,
    status: str | None = None,
    actor_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": uuid.uuid4().hex,
        "task_id": task_id,
        "event_type": event_type,
        "status": status,
        "actor_id": actor_id,
        "occurred_at": now_iso(),
        "details": privacy_safe_details(details or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, (canonical_json(event) + "\n").encode("utf-8"))
        os.fsync(fd)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    return event
