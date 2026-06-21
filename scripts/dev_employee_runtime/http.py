from __future__ import annotations

import json
from typing import Any


def parse_json_response(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
