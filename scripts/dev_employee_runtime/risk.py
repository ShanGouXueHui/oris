from __future__ import annotations

from enum import IntEnum


class RiskTier(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def parse(cls, value: object) -> "RiskTier":
        normalized = str(value or "").strip().upper()
        try:
            return cls[normalized]
        except KeyError as exc:
            raise ValueError(f"invalid risk tier: {value}") from exc
