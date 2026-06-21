from __future__ import annotations

from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")
