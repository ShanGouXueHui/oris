from __future__ import annotations

from datetime import datetime, timezone


def utc_compact_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
