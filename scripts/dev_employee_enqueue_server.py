#!/usr/bin/env python3
"""Local-only ORIS Dev Employee enqueue HTTP server.

This server is the narrow bridge between OpenClaw Web/task intake and the
host-side supervised bridge service. It only creates local queued task JSON
files and exposes read-only task status. It never executes shell commands,
never invokes Codex directly, and never pushes GitHub.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ORIS_DIR = Path("/home/admin/projects/oris")
PROJECTS_DIR = Path("/home/admin/projects")
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
DEFAULT_CODEX = Path("/home/admin/.npm-global/bin/codex")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18891
TASK_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$")


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


def safe_resolve(path_value: str, roots: list[Path], must_exist: bool = False) -> Path:
    path = Path(path_value).expanduser().resolve()
    resolved_roots = [root.resolve() for root in roots]
    if not any(path == root or root in path.parents for root in resolved_roots):
        raise ValueError(f"path outside allowed roots: {path}")
    if must_exist and not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_descriptor(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id", "")).strip()
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id; use 3-120 chars: letters, digits, dot, underscore, dash")

    prompt_path = safe_resolve(str(payload["prompt_path"]), [ORIS_DIR, PROJECTS_DIR], must_exist=True)
    product_path = safe_resolve(str(payload["product_path"]), [PROJECTS_DIR], must_exist=True)
    workdir = safe_resolve(str(payload.get("workdir") or PROJECTS_DIR), [PROJECTS_DIR], must_exist=True)
    codex_bin = safe_resolve(str(payload.get("codex_bin") or DEFAULT_CODEX), [Path("/home/admin")], must_exist=True)
    product_repo = str(payload["product_repo"])
    commit_message = str(payload["commit_message"])

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    target = QUEUE_DIR / f"{task_id}.queued.json"
    for suffix in ["queued", "running", "done", "failed"]:
        existing = QUEUE_DIR / f"{task_id}.{suffix}.json"
        if existing.exists():
            raise FileExistsError(f"task descriptor already exists: {existing}")

    descriptor = {
        "task_id": task_id,
        "status": "queued",
        "created_at": now_iso(),
        "created_by": "dev_employee_enqueue_server",
        "prompt_path": str(prompt_path),
        "workdir": str(workdir),
        "codex_bin": str(codex_bin),
        "sandbox": str(payload.get("sandbox") or "workspace-write"),
        "extra_write_dirs": [str(ORIS_DIR)],
        "expected_product_repo": product_repo,
        "expected_product_path": str(product_path),
        "product_commit_message": commit_message,
        "notes": str(payload.get("note") or "Queued by dev_employee_enqueue_server.py"),
    }
    write_json(target, descriptor)
    return {"queued": True, "task_id": task_id, "path": str(target), "descriptor": descriptor}


def auth_ok(handler: BaseHTTPRequestHandler) -> bool:
    token = os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN")
    if not token:
        return os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_ALLOW_NO_TOKEN") == "1"
    provided = handler.headers.get("X-ORIS-Token") or ""
    return provided == token


def task_status(task_id: str) -> dict[str, Any]:
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")

    queue_matches = []
    if QUEUE_DIR.exists():
        for suffix in ["queued", "running", "done", "failed"]:
            path = QUEUE_DIR / f"{task_id}.{suffix}.json"
            if path.exists():
                try:
                    queue_matches.append({"suffix": suffix, "path": str(path), "data": read_json(path)})
                except Exception as exc:
                    queue_matches.append({"suffix": suffix, "path": str(path), "error": repr(exc)})

    run_files = []
    if RUN_DIR.exists():
        for path in sorted(RUN_DIR.glob(f"{task_id}*.json")):
            try:
                run_files.append({"path": str(path), "data": read_json(path)})
            except Exception as exc:
                run_files.append({"path": str(path), "error": repr(exc)})

    latest = None
    latest_path = LOG_DIR / "latest_task_progress.json"
    if latest_path.exists():
        try:
            latest = read_json(latest_path)
        except Exception as exc:
            latest = {"error": repr(exc)}

    status = "unknown"
    if run_files:
        first_data = run_files[0].get("data") or {}
        status = str(first_data.get("status") or status)
    elif queue_matches:
        status = str((queue_matches[0].get("data") or {}).get("status") or queue_matches[0].get("suffix") or status)

    return {
        "task_id": task_id,
        "status": status,
        "queue": queue_matches,
        "runs": run_files,
        "latest_task_progress": latest,
    }


def latest_status() -> dict[str, Any]:
    latest_path = LOG_DIR / "latest_task_progress.json"
    if not latest_path.exists():
        return {"status": "not_found", "path": str(latest_path)}
    return {"status": "ok", "path": str(latest_path), "data": read_json(latest_path)}


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-enqueue/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            return json_response(self, 200, {"status": "ok", "service": "dev_employee_enqueue_server"})
        if path == "/queue":
            items = sorted(p.name for p in QUEUE_DIR.glob("*.json")) if QUEUE_DIR.exists() else []
            return json_response(self, 200, {"queue_dir": str(QUEUE_DIR), "items": items})
        if path == "/latest":
            return json_response(self, 200, latest_status())
        if path.startswith("/task/"):
            task_id = unquote(path.removeprefix("/task/")).strip()
            try:
                return json_response(self, 200, task_status(task_id))
            except Exception as exc:
                return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/enqueue":
            return json_response(self, 404, {"error": "not_found"})
        if not auth_ok(self):
            return json_response(self, 401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 64_000:
                return json_response(self, 400, {"error": "invalid_body_length"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = create_descriptor(payload)
            return json_response(self, 201, result)
        except Exception as exc:
            return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS enqueue server listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
