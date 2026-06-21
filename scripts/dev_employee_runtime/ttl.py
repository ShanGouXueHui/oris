from __future__ import annotations


def require_ttl_seconds(value: object, *, minimum: int, maximum: int) -> int:
    seconds = int(value)
    if seconds < minimum or seconds > maximum:
        raise ValueError(f"TTL must be between {minimum} and {maximum} seconds")
    return seconds
