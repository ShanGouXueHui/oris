from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectAuthorization:
    allowed: bool
    reason: str
    project_key: str
    action: str


def authorize_project_action(
    *,
    project_key: str,
    action: str,
    allowed_actions: tuple[str, ...],
) -> ProjectAuthorization:
    if action not in allowed_actions:
        return ProjectAuthorization(False, "action_not_allowed_for_project", project_key, action)
    return ProjectAuthorization(True, "project_action_allowed", project_key, action)
