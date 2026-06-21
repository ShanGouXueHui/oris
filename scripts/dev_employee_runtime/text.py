from __future__ import annotations

from typing import Any


def bounded_text(value: Any, *, name: str, minimum: int = 1, maximum: int) -> str:
    text = str(value or "").strip()
    if len(text) < minimum:
        raise ValueError(f"{name} is too short")
    if len(text) > maximum:
        raise ValueError(f"{name} is too long")
    return text


def bounded_text_list(
    value: Any,
    *,
    name: str,
    max_items: int,
    max_length: int,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    if len(value) > max_items:
        raise ValueError(f"{name} exceeds item limit")
    items: list[str] = []
    for raw in value:
        text = str(raw).strip()
        if not text:
            continue
        if len(text) > max_length:
            raise ValueError(f"{name} item is too long")
        items.append(text)
    return tuple(items)
