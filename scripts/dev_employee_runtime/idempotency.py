from __future__ import annotations

import hashlib
from typing import Any

from .json_store import canonical_json


def request_fingerprint(payload: dict[str, Any]) -> str:
    normalized = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "created_at",
            "updated_at",
            "runtime",
            "lease_token",
            "worker_id",
            "worker_pid",
        }
    }
    return hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()
