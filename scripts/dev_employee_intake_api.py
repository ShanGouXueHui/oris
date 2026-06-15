#!/usr/bin/env python3
"""Local-only ORIS Dev Employee intake and status API.

This is a thin productized layer for OpenClaw/Web/non-shell users. It accepts a
business goal plus constraints, resolves the target project from
orchestration/project_registry.json, writes a runtime prompt, submits the task to
the existing loopback enqueue API, and persists a small intake catalog record.

Safety boundaries:
- Binds only to loopback.
- Does not execute shell commands.
- Does not invoke Codex directly.
- Does not commit or push Git.
- Uses the existing enqueue API and supervised bridge for execution.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from dev_employee_task_states import classify as classify_task_state

ORIS_DIR = Path("/home/admin/projects/oris")
ORIS_REPO = "ShanGouXueHui/oris"
DEFAULT_BRANCH = "main"
REGISTRY = ORIS_DIR / "orchestration" / "project_registry.json"
CATALOG_DIR = ORIS_DIR / "orchestration" / "dev_employee_intake_catalog"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
EVIDENCE_COMMIT_INDEX_DIR = LOG_DIR / "evidence_commit_index"
BASE_TEMPLATE = ORIS_DIR / "prompts" / "dev_employee_autonomous_development_task_template_20260526.md"
RUNTIME_PROMPT_DIR = ORIS_DIR / "run" / "dev_employee_prompts"
DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
DEFAULT_ENQUEUE_URL = "http://127.0.0.1:18891/enqueue"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18892
TASK_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$")
PROJECT_KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,80}$")
AUTH_HEADER = "X-ORIS-Token"
ENQUEUE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN"
INTAKE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_INTAKE_TOKEN"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


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
    if not str(local_path).startswith("/home/admin/projects/"):
        raise ValueError(f"project local_path outside /home/admin/projects: {local_path}")
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
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
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


def write_runtime_prompt(task_id: str, objective: str, constraints: list[str], checks: list[str], project: dict[str, Any]) -> Path:
    if not BASE_TEMPLATE.exists():
        raise FileNotFoundError(f"base prompt template not found: {BASE_TEMPLATE}")
    base = BASE_TEMPLATE.read_text(encoding="utf-8")
    RUNTIME_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = RUNTIME_PROMPT_DIR / f"{task_id}.md"
    constraint_lines = "\n".join(f"- {item}" for item in constraints) if constraints else "- Follow existing ORIS project policies and safety boundaries."
    check_lines = "\n".join(f"- `{item}`" for item in checks) if checks else "- Decide and run the relevant local checks for the product stack."
    content = (
        base
        + "\n\n---\n\n"
        + "# CONCRETE AUTONOMOUS PRODUCT GOAL\n\n"
        + objective.strip()
        + "\n\n"
        + "## Target project\n\n"
        + f"- project_key: `{project['project_key']}`\n"
        + f"- product_repo: `{project['product_repo']}`\n"
        + f"- product_path: `{project['product_path']}`\n"
        + "\n## Human constraints\n\n"
        + constraint_lines
        + "\n\n"
        + "## Expected checks\n\n"
        + check_lines
        + "\n\n"
        + "## Autonomy instruction\n\n"
        + "Do not ask the human to choose routine engineering steps. Decide the plan, implement, test, repair ordinary failures, and write structured evidence. Block only on the doctrine-defined boundaries.\n"
    )
    prompt_path.write_text(content, encoding="utf-8")
    return prompt_path


def post_enqueue(payload: dict[str, Any]) -> tuple[int, Any]:
    url = os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_URL", DEFAULT_ENQUEUE_URL)
    if not url.startswith("http://127.0.0.1:") and not url.startswith("http://localhost:"):
        raise RuntimeError("refusing non-loopback enqueue URL")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", AUTH_HEADER: enqueue_token()},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text)
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(text)
        except json.JSONDecodeError:
            return exc.code, {"raw": text}
    except urllib.error.URLError as exc:
        return 599, {"error": "url_error", "message": str(exc)}


def annotate_descriptor(enqueue_response: Any, objective: str, constraints: list[str], checks: list[str]) -> dict[str, Any]:
    if not isinstance(enqueue_response, dict):
        return {"annotated": False, "reason": "response_not_object"}
    path_value = enqueue_response.get("path")
    if not path_value:
        response = enqueue_response.get("response") if isinstance(enqueue_response.get("response"), dict) else {}
        path_value = response.get("path")
    if not path_value:
        return {"annotated": False, "reason": "missing_descriptor_path"}
    path = Path(str(path_value))
    if not path.exists():
        return {"annotated": False, "reason": "descriptor_already_claimed_or_missing", "path": str(path)}
    data = read_json(path)
    data.update(
        {
            "strict_result_schema": True,
            "autonomy_mode": "goal_driven",
            "task_objective": objective,
            "constraints": constraints,
            "expected_checks": checks,
        }
    )
    write_json(path, data)
    return {"annotated": True, "path": str(path)}


def create_goal(payload: dict[str, Any]) -> dict[str, Any]:
    project_key = str(payload.get("project_key") or "").strip()
    project = resolve_project(project_key)
    objective = str(payload.get("objective") or "").strip()
    if len(objective) < 20:
        raise ValueError("objective must be at least 20 characters")
    if len(objective) > 12_000:
        raise ValueError("objective too long")
    task_id = str(payload.get("task_id") or default_task_id(project_key)).strip()
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")
    constraints = sanitize_list(payload.get("constraints"), "constraints")
    checks = sanitize_list(payload.get("expected_checks"), "expected_checks")
    notes = sanitize_list(payload.get("notes"), "notes", max_items=10)
    commit_message = str(payload.get("commit_message") or f"feat(dev-employee): complete {task_id}").strip()[:200]
    prompt_path = write_runtime_prompt(task_id, objective, constraints, checks, project)
    enqueue_payload = {
        "task_id": task_id,
        "prompt_path": str(prompt_path),
        "product_path": project["product_path"],
        "product_repo": project["product_repo"],
        "commit_message": commit_message,
        "note": notes[0] if notes else "Queued by dev_employee_intake_api.py",
        "strict_result_schema": True,
        "task_objective": objective,
        "constraints": constraints,
        "expected_checks": checks,
    }
    http_status, enqueue_response = post_enqueue(enqueue_payload)
    descriptor_annotation = None
    if 200 <= http_status < 300:
        descriptor_annotation = annotate_descriptor(enqueue_response, objective, constraints, checks)
    catalog = {
        "task_id": task_id,
        "project_key": project_key,
        "project": project,
        "objective": objective,
        "constraints": constraints,
        "expected_checks": checks,
        "commit_message": commit_message,
        "notes": notes,
        "status": "queued" if 200 <= http_status < 300 else "enqueue_failed",
        "created_at": now_iso(),
        "runtime_prompt_path": str(prompt_path),
        "enqueue_http_status": http_status,
        "enqueue_response": enqueue_response,
        "descriptor_annotation": descriptor_annotation,
    }
    write_json(CATALOG_DIR / f"{task_id}.json", catalog)
    return catalog


def repo_relative(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(ORIS_DIR.resolve()).as_posix()
    except ValueError:
        return None


def evidence_file(label: str, path: Path) -> dict[str, Any]:
    rel = repo_relative(path)
    return {
        "label": label,
        "exists": path.exists(),
        "local_path": str(path),
        "repo": ORIS_REPO if rel else None,
        "branch": DEFAULT_BRANCH if rel else None,
        "repo_path": rel,
    }


def evidence_summary(task_id: str, primary_run: dict[str, Any] | None) -> dict[str, Any]:
    index_path = EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"
    evidence_index = read_json(index_path) if index_path.exists() else {}
    files = [
        evidence_file("task_run_json", RUN_DIR / f"{task_id}.json"),
        evidence_file("codex_result_json", RUN_DIR / f"{task_id}.codex_result.json"),
        evidence_file("skill_resolution_json", LOG_DIR / "skill_resolution" / f"{task_id}.json"),
        evidence_file("skill_resolution_markdown", LOG_DIR / "skill_resolution" / f"{task_id}.md"),
        evidence_file("codex_log", LOG_DIR / f"{task_id}.codex.log"),
        evidence_file("host_py_compile_log", LOG_DIR / f"{task_id}_host_py_compile.txt"),
        evidence_file("host_pytest_log", LOG_DIR / f"{task_id}_host_pytest.txt"),
        evidence_file("host_pytest_werror_log", LOG_DIR / f"{task_id}_host_pytest_werror.txt"),
        evidence_file("evidence_commit_index", EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"),
    ]
    completed = primary_run or {}
    return {
        "repo": ORIS_REPO,
        "branch": DEFAULT_BRANCH,
        "files": [item for item in files if item["exists"]],
        "product_commit_sha": completed.get("product_commit_sha"),
        "product_remote_sha": completed.get("product_remote_sha"),
        "oris_evidence_sha": completed.get("oris_evidence_sha"),
        "oris_evidence_commit_sha": evidence_index.get("oris_evidence_commit_sha"),
        "oris_evidence_remote_sha": evidence_index.get("oris_evidence_remote_sha"),
        "evidence_index_commit_sha": evidence_index.get("evidence_index_commit_sha"),
        "strict_result_schema": completed.get("strict_result_schema"),
        "skill_resolver_report_json": completed.get("skill_resolver_report_json"),
    }


def task_status(task_id: str) -> dict[str, Any]:
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")
    catalog_path = CATALOG_DIR / f"{task_id}.json"
    catalog = read_json(catalog_path) if catalog_path.exists() else None
    queue = []
    seen_queue_paths: set[Path] = set()
    for suffix in ["queued", "running", "done", "failed"]:
        candidates = [QUEUE_DIR / f"{task_id}.{suffix}.json"]
        candidates.extend(sorted(QUEUE_DIR.glob(f"{task_id}*.{suffix}.json")))
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen_queue_paths or not path.exists():
                continue
            seen_queue_paths.add(resolved)
            queue.append({"suffix": suffix, "path": str(path), "data": read_json(path)})
    runs = []
    for path in sorted(RUN_DIR.glob(f"{task_id}*.json")) if RUN_DIR.exists() else []:
        runs.append({"path": str(path), "data": read_json(path)})
    primary_run = read_json(RUN_DIR / f"{task_id}.json") if (RUN_DIR / f"{task_id}.json").exists() else None
    status = "unknown"
    if primary_run:
        status = str(primary_run.get("status") or status)
    elif runs:
        status = str((runs[0].get("data") or {}).get("status") or status)
    elif queue:
        status = str((queue[0].get("data") or {}).get("status") or queue[0].get("suffix") or status)
    elif catalog:
        status = str(catalog.get("status") or status)
    state = classify_task_state(status, primary_run or {})
    latest = None
    latest_path = LOG_DIR / "latest_task_progress.json"
    if latest_path.exists():
        latest = read_json(latest_path)
    evidence = {
        "task_run_json": str(RUN_DIR / f"{task_id}.json") if (RUN_DIR / f"{task_id}.json").exists() else None,
        "codex_result_json": str(RUN_DIR / f"{task_id}.codex_result.json") if (RUN_DIR / f"{task_id}.codex_result.json").exists() else None,
        "skill_resolution_json": str(LOG_DIR / "skill_resolution" / f"{task_id}.json") if (LOG_DIR / "skill_resolution" / f"{task_id}.json").exists() else None,
        "codex_log": str(LOG_DIR / f"{task_id}.codex.log") if (LOG_DIR / f"{task_id}.codex.log").exists() else None,
    }
    return {
        "task_id": task_id,
        "status": status,
        "canonical_status": state["canonical_status"],
        "terminal": state["terminal"],
        "failure_code": state["failure_code"],
        "catalog": catalog,
        "queue": queue,
        "runs": runs,
        "latest_task_progress": latest,
        "evidence": evidence,
        "github_evidence": evidence_summary(task_id, primary_run),
    }


def list_goals() -> dict[str, Any]:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(CATALOG_DIR.glob("*.json")):
        data = read_json(path)
        task_id = str(data.get("task_id") or "")
        current = task_status(task_id) if task_id else {}
        items.append({
            "task_id": task_id or None,
            "project_key": data.get("project_key"),
            "status": current.get("status") or data.get("status"),
            "canonical_status": current.get("canonical_status"),
            "terminal": current.get("terminal"),
            "failure_code": current.get("failure_code"),
            "created_at": data.get("created_at"),
            "path": str(path),
        })
    return {"catalog_dir": str(CATALOG_DIR), "items": items}


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-intake/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            return json_response(self, 200, {"status": "ok", "service": "dev_employee_intake_api"})
        if path == "/projects":
            projects = registry().get("projects", {})
            return json_response(self, 200, {"projects": sorted(projects.keys())})
        if path == "/goals":
            return json_response(self, 200, list_goals())
        if path.startswith("/goals/"):
            task_id = unquote(path.removeprefix("/goals/")).strip()
            try:
                return json_response(self, 200, task_status(task_id))
            except Exception as exc:
                return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/goals":
            return json_response(self, 404, {"error": "not_found"})
        if not auth_ok(self):
            return json_response(self, 401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 80_000:
                return json_response(self, 400, {"error": "invalid_body_length"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = create_goal(payload)
            status = 201 if result.get("status") == "queued" else 502
            return json_response(self, status, result)
        except Exception as exc:
            return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS intake API listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
