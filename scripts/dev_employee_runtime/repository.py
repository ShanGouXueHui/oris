from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .json_store import read_json
from .settings import RuntimeSettings


@dataclass(frozen=True)
class AuthorizedProject:
    project_key: str
    name: str
    project_type: str
    local_path: Path
    github_full_name: str
    default_branch: str
    allowed_scope: tuple[str, ...]
    forbidden_scope: tuple[str, ...]


def github_full_name(project: dict[str, Any]) -> str:
    github = str(project.get("github") or "").strip()
    if github.startswith("https://github.com/"):
        return github.removeprefix("https://github.com/").strip("/")
    repo = str(project.get("repo") or "").strip()
    if repo.startswith("git@github.com:") and repo.endswith(".git"):
        return repo.removeprefix("git@github.com:").removesuffix(".git")
    raise ValueError("project registry entry lacks resolvable GitHub repository")


def resolve_project(
    registry_path: Path,
    project_key: str,
    settings: RuntimeSettings,
) -> AuthorizedProject:
    projects = read_json(registry_path).get("projects")
    if not isinstance(projects, dict):
        raise ValueError("project registry projects must be an object")
    project = projects.get(project_key)
    if not isinstance(project, dict):
        raise KeyError(f"unknown project_key: {project_key}")
    local_path = settings.require_project_path(Path(str(project.get("local_path") or "")))
    return AuthorizedProject(
        project_key=project_key,
        name=str(project.get("name") or project_key),
        project_type=str(project.get("type") or "unknown"),
        local_path=local_path,
        github_full_name=github_full_name(project),
        default_branch=str(project.get("default_branch") or settings.default_branch),
        allowed_scope=tuple(str(item) for item in project.get("allowed_scope") or []),
        forbidden_scope=tuple(str(item) for item in project.get("forbidden_scope") or []),
    )
