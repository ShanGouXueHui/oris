from __future__ import annotations

import hashlib
from typing import Any

from .json_store import canonical_json


_PRIVATE_KEYS = {
    "conversation",
    "conversation_content",
    "prompt",
    "raw_session_id",
    "session_id",
    "tool_args",
    "tool_results",
    "token",
    "secret",
}


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def privacy_safe_details(details: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in details.items():
        normalized = key.lower()
        if normalized in _PRIVATE_KEYS or "token" in normalized or "secret" in normalized:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, (list, tuple)):
            safe[key] = [item for item in value if isinstance(item, (str, int, float, bool))]
        elif isinstance(value, dict):
            safe[key] = privacy_safe_details(value)
    return safe
