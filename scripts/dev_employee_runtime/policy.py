from __future__ import annotations

from dataclasses import dataclass

from .risk import RiskTier


@dataclass(frozen=True)
class ActionPolicy:
    action: str
    permission: str
    risk_tier: RiskTier
    approval_required: bool
    separation_required: bool
    approval_ttl_seconds: int
    operation_ttl_seconds: int


@dataclass(frozen=True)
class ProjectPolicy:
    profile: str
    allowed_actions: tuple[str, ...]
    writable_scopes: tuple[str, ...]
    denied_scopes: tuple[str, ...]
