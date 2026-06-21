from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RbacDecision:
    allowed: bool
    reason: str
    matched_role: str | None = None
    matched_permission: str | None = None


def evaluate_permission(
    actor_roles: tuple[str, ...],
    required_permission: str,
    role_permissions: dict[str, tuple[str, ...]],
) -> RbacDecision:
    for role in actor_roles:
        permissions = role_permissions.get(role, ())
        if required_permission in permissions:
            return RbacDecision(True, "permission_allowed", role, required_permission)
    return RbacDecision(False, "permission_denied", None, required_permission)
