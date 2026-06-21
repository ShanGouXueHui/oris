from __future__ import annotations

from typing import Any

from .audit import stable_hash


def chained_hash(previous_hash: str | None, event: dict[str, Any]) -> str:
    return stable_hash({"previous_hash": previous_hash or "", "event": event})
