from __future__ import annotations

from typing import Any

from .task_contract import require_unique_strings


def unique_string_list(value: Any, label: str) -> list[str]:
    return list(require_unique_strings(value, label))
