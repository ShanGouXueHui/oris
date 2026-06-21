from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reasons: tuple[str, ...]


def combine_decisions(*decisions: tuple[bool, str]) -> PolicyDecision:
    denied = tuple(reason for allowed, reason in decisions if not allowed)
    return PolicyDecision(not denied, denied or ("allowed",))
