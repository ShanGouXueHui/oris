from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.env import load_env
from dev_employee_runtime.json_store import read_json
from dev_employee_runtime.paths import discover_repo_root
from dev_employee_runtime.settings import load_runtime_settings

ORIS_DIR = discover_repo_root()
RUNTIME_SETTINGS = load_runtime_settings(ORIS_DIR)
ORIS_REPO = "ShanGouXueHui/oris"
DEFAULT_BRANCH = RUNTIME_SETTINGS.default_branch
REGISTRY = ORIS_DIR / "orchestration" / "project_registry.json"
CATALOG_DIR = ORIS_DIR / "orchestration" / "dev_employee_intake_catalog"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
EVIDENCE_COMMIT_INDEX_DIR = LOG_DIR / "evidence_commit_index"
BASE_TEMPLATE = ORIS_DIR / "prompts" / "dev_employee_autonomous_development_task_template_20260526.md"
RUNTIME_PROMPT_DIR = ORIS_DIR / "run" / "dev_employee_prompts"
DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
DEFAULT_ENQUEUE_URL = f"{RUNTIME_SETTINGS.queue_url}/enqueue"
DEFAULT_HOST = RUNTIME_SETTINGS.intake_host
DEFAULT_PORT = RUNTIME_SETTINGS.intake_port
TASK_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$")
PROJECT_KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,80}$")
AUTH_HEADER = "X-ORIS-Token"
ENQUEUE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN"
INTAKE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_INTAKE_TOKEN"


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def auth_ok(handler: BaseHTTPRequestHandler) -> bool:
    token = os.environ.get(INTAKE_TOKEN_KEY)
    if not token:
        token = load_env(DEFAULT_ENV_FILE).get(INTAKE_TOKEN_KEY)
    if not token:
        return os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_ALLOW_NO_TOKEN") == "1"
    return (handler.headers.get(AUTH_HEADER) or "") == token


def enqueue_token() -> str:
    token = os.environ.get(ENQUEUE_TOKEN_KEY) or load_env(DEFAULT_ENV_FILE).get(ENQUEUE_TOKEN_KEY)
    if not token:
        raise RuntimeError(f"{ENQUEUE_TOKEN_KEY} missing from environment or {DEFAULT_ENV_FILE}")
    return token


def registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        raise RuntimeError(f"project registry not found: {REGISTRY}")
    return read_json(REGISTRY)


def github_full_name(project: dict[str, Any]) -> str:
    github = str(project.get("github") or "")
    if github.startswith("https://github.com/"):
        return github.removeprefix("https://github.com/").strip("/")
    repo = str(project.get("repo") or "")
    if repo.startswith("git@github.com:") and repo.endswith(".git"):
        return repo.removeprefix("git@github.com:").removesuffix(".git")
    raise ValueError("project registry entry lacks resolvable GitHub repo")


def resolve_project(project_key: str) -> dict[str, Any]:
    if not PROJECT_KEY_RE.match(project_key):
        raise ValueError("invalid project_key")
    projects = registry().get("projects", {})
    project = projects.get(project_key)
    if not isinstance(project, dict):
        raise KeyError(f"unknown project_key: {project_key}")
    local_path = Path(str(project.get("local_path") or "")).expanduser().resolve()
    projects_root = RUNTIME_SETTINGS.projects_root.resolve()
    try:
        local_path.relative_to(projects_root)
    except ValueError as exc:
        raise ValueError(f"project local_path outside configured projects root: {local_path}") from exc
    if not local_path.exists():
        raise FileNotFoundError(f"project local_path does not exist: {local_path}")
    return {
        "project_key": project_key,
        "name": project.get("name"),
        "type": project.get("type"),
        "product_path": str(local_path),
        "product_repo": github_full_name(project),
        "default_branch": project.get("default_branch") or DEFAULT_BRANCH,
        "allowed_scope": project.get("allowed_scope", []),
        "forbidden_scope": project.get("forbidden_scope", []),
    }


def default_task_id(project_key: str) -> str:
    stamp = now_iso().replace("-", "").replace(":", "").split("+")[0]
    return f"goal-{project_key}-{stamp}"


def sanitize_list(value: Any, name: str, max_items: int = 30) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    result: list[str] = []
    for item in value[:max_items]:
        text = str(item).strip()
        if text:
            result.append(text[:2000])
    return result
