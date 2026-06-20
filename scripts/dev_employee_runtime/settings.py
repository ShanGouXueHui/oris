from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS_PATH = Path("config/dev_employee/runtime_settings.json")


@dataclass(frozen=True)
class RuntimeSettings:
    repo_root: Path
    projects_root: Path
    queue_url: str
    intake_url: str
    enqueue_host: str
    enqueue_port: int
    intake_host: str
    intake_port: int
    web_console_host: str
    web_console_port: int
    default_branch: str

    def require_project_path(self, candidate: Path) -> Path:
        resolved = candidate.expanduser().resolve()
        resolved.relative_to(self.projects_root.resolve())
        return resolved


def _text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"runtime setting is required: {key}")
    return value


def _port(payload: dict[str, Any], key: str) -> int:
    value = int(payload.get(key) or 0)
    if value < 1 or value > 65535:
        raise ValueError(f"invalid runtime port: {key}")
    return value


def load_runtime_settings(
    repo_root: Path,
    relative_path: Path = DEFAULT_SETTINGS_PATH,
) -> RuntimeSettings:
    payload = json.loads((repo_root / relative_path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported runtime settings schema_version")
    configured_repo = Path(_text(payload, "repo_root")).expanduser().resolve()
    if configured_repo != repo_root.resolve():
        raise ValueError("runtime settings repo_root does not match active repository")
    return RuntimeSettings(
        repo_root=configured_repo,
        projects_root=Path(_text(payload, "projects_root")).expanduser().resolve(),
        queue_url=_text(payload, "queue_url"),
        intake_url=_text(payload, "intake_url"),
        enqueue_host=_text(payload, "enqueue_host"),
        enqueue_port=_port(payload, "enqueue_port"),
        intake_host=_text(payload, "intake_host"),
        intake_port=_port(payload, "intake_port"),
        web_console_host=_text(payload, "web_console_host"),
        web_console_port=_port(payload, "web_console_port"),
        default_branch=_text(payload, "default_branch"),
    )
