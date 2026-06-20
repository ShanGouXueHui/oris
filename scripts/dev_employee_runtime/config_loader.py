from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_object(path: Path, *, schema_version: int | None = None) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"configuration must be a JSON object: {path}")
    if schema_version is not None and payload.get("schema_version") != schema_version:
        raise ValueError(f"unsupported schema_version in {path}")
    return payload
