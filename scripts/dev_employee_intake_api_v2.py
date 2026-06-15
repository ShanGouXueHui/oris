#!/usr/bin/env python3
"""ORIS Dev Employee intake/status/control API v2.

v2 preserves the verified loopback and enqueue boundaries while adding:

- task-id idempotency with request fingerprints and conflict detection;
- accepted/validated/queued event ledger entries;
- lifecycle/lease/cancellation visibility;
- authenticated cancel and explicit retry control endpoints;
- retry lineage and bounded attempts;
- no direct shell, Codex, product mutation, or Git push.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import dev_employee_intake_api as v1
from dev_employee_queue_kernel import (
    DEFAULT_KERNEL,
    TaskConflict,
    TaskNotFound,
    atomic_write_json,
    generate_retry_task_id,
    now_iso,
    read_json,
    request_fingerprint,
)
from dev_employee_task_states import classify as classify_task_state

DEFAULT_HOST = v1.DEFAULT_HOST
DEFAULT_PORT = v1.DEFAULT_PORT
CATALOG_DIR = v1.CATALOG_DIR
QUEUE_DIR = v1.QUEUE_DIR
TASK_ID_RE = v1.TASK_ID_RE


class IntakeConflict(TaskConflict):
    pass


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    return v1.json_response(handler, status, payload)


def normalized_request(
    *,
    project_key: str,
    objective: str,
    constraints: list[str],
    checks: list[str],
    commit_message: str,
    retry_of: str | None,
    attempt: int,
) -> dict[str, Any]:
    return {
        "project_key": project_key,
        "objective": objective,
        "constraints": constraints,
        "expected_checks": checks,
        "commit_message": commit_message,
        "retry_of": retry_of,
        "attempt": attempt,
    }


def catalog_fingerprint(catalog: dict[str, Any]) -> str:
    existing = catalog.get("request_fingerprint")
    if existing:
        return str(existing)
    return request_fingerprint(
        normalized_request(
            project_key=str(catalog.get("project_key") or ""),
            objective=str(catalog.get("objective") or ""),
            constraints=list(catalog.get("constraints") or []),
            checks=list(catalog.get("expected_checks") or []),
            commit_message=str(catalog.get("commit_message") or ""),
            retry_of=str(catalog.get("retry_of") or "") or None,
            attempt=int(catalog.get("attempt") or 1),
        )
    )


def annotate_lifecycle_descriptor(
    descriptor_annotation: dict[str, Any] | None,
    lifecycle: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(descriptor_annotation, dict) or not descriptor_annotation.get("annotated"):
        return descriptor_annotation
    path_value = descriptor_annotation.get("path")
    if not path_value:
        return descriptor_annotation
    path = Path(str(path_value))
    if not path.exists():
        return {**descriptor_annotation, "lifecycle_annotation": "descriptor_already_claimed"}
    descriptor = read_json(path)
    descriptor.update(lifecycle)
    atomic_write_json(path, descriptor)
    return {**descriptor_annotation, "lifecycle_annotation": "applied"}


def create_goal(payload: dict[str, Any]) -> dict[str, Any]:
    project_key = str(payload.get("project_key") or "").strip()
    project = v1.resolve_project(project_key)
    objective = str(payload.get("objective") or "").strip()
    if len(objective) < 20:
        raise ValueError("objective must be at least 20 characters")
    if len(objective) > 12_000:
        raise ValueError("objective too long")

    task_id = str(payload.get("task_id") or v1.default_task_id(project_key)).strip()
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")
    constraints = v1.sanitize_list(payload.get("constraints"), "constraints")
    checks = v1.sanitize_list(payload.get("expected_checks"), "expected_checks")
    notes = v1.sanitize_list(payload.get("notes"), "notes", max_items=10)
    commit_message = str(payload.get("commit_message") or f"feat(dev-employee): complete {task_id}").strip()[:200]
    retry_of = str(payload.get("retry_of") or "").strip() or None
    root_task_id = str(payload.get("root_task_id") or retry_of or task_id).strip()
    attempt = max(1, int(payload.get("attempt") or 1))
    max_attempts = max(1, min(20, int(payload.get("max_attempts") or 3)))
    if attempt > max_attempts:
        raise IntakeConflict(f"attempt {attempt} exceeds max_attempts {max_attempts}")
    lease_seconds = max(15, min(3600, int(payload.get("lease_seconds") or 60)))
    execution_timeout_seconds = max(60, min(86_400, int(payload.get("execution_timeout_seconds") or 7200)))

    request_data = normalized_request(
        project_key=project_key,
        objective=objective,
        constraints=constraints,
        checks=checks,
        commit_message=commit_message,
        retry_of=retry_of,
        attempt=attempt,
    )
    fingerprint = request_fingerprint(request_data)
    catalog_path = CATALOG_DIR / f"{task_id}.json"
    if catalog_path.exists():
        existing = read_json(catalog_path)
        if catalog_fingerprint(existing) != fingerprint:
            raise IntakeConflict(f"task_id already exists with a different request: {task_id}")
        replay = dict(existing)
        replay["idempotent_replay"] = True
        replay["current_status"] = task_status(task_id)
        return replay

    DEFAULT_KERNEL.append_event(
        task_id,
        "task_accepted",
        status="accepted",
        actor="intake-api-v2",
        details={"project_key": project_key, "request_fingerprint": fingerprint, "attempt": attempt},
    )
    DEFAULT_KERNEL.append_event(
        task_id,
        "task_validated",
        status="validated",
        actor="intake-api-v2",
        details={"project_key": project_key, "root_task_id": root_task_id, "retry_of": retry_of},
    )

    prompt_path = v1.write_runtime_prompt(task_id, objective, constraints, checks, project)
    lifecycle_fields = {
        "attempt": attempt,
        "max_attempts": max_attempts,
        "retry_of": retry_of,
        "root_task_id": root_task_id,
        "request_fingerprint": fingerprint,
        "lease_seconds": lease_seconds,
        "execution_timeout_seconds": execution_timeout_seconds,
    }
    enqueue_payload = {
        "task_id": task_id,
        "prompt_path": str(prompt_path),
        "product_path": project["product_path"],
        "product_repo": project["product_repo"],
        "commit_message": commit_message,
        "note": notes[0] if notes else "Queued by dev_employee_intake_api_v2.py",
        "strict_result_schema": True,
        "task_objective": objective,
        "constraints": constraints,
        "expected_checks": checks,
        **lifecycle_fields,
    }
    http_status, enqueue_response = v1.post_enqueue(enqueue_payload)
    descriptor_annotation = None
    if 200 <= http_status < 300:
        descriptor_annotation = v1.annotate_descriptor(enqueue_response, objective, constraints, checks)
        descriptor_annotation = annotate_lifecycle_descriptor(descriptor_annotation, lifecycle_fields)

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
        "request_fingerprint": fingerprint,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "retry_of": retry_of,
        "root_task_id": root_task_id,
        "lease_seconds": lease_seconds,
        "execution_timeout_seconds": execution_timeout_seconds,
        "retries": [],
    }
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(catalog_path, catalog)
    if 200 <= http_status < 300:
        DEFAULT_KERNEL.append_event(
            task_id,
            "task_queued",
            status="queued",
            actor="intake-api-v2",
            details={"enqueue_http_status": http_status, "descriptor_annotation": descriptor_annotation},
        )
    else:
        DEFAULT_KERNEL.append_event(
            task_id,
            "enqueue_failed",
            status="failed",
            actor="intake-api-v2",
            details={"enqueue_http_status": http_status},
        )
    return catalog


def task_status(task_id: str) -> dict[str, Any]:
    result = v1.task_status(task_id)
    cancelled_path = DEFAULT_KERNEL.task_path(task_id, "cancelled")
    if cancelled_path.exists():
        cancelled_data = read_json(cancelled_path)
        queue = result.get("queue") if isinstance(result.get("queue"), list) else []
        if not any(item.get("suffix") == "cancelled" for item in queue if isinstance(item, dict)):
            queue.append({"suffix": "cancelled", "path": str(cancelled_path), "data": cancelled_data})
        state = classify_task_state(cancelled_data.get("status") or "cancelled", cancelled_data)
        result.update(
            {
                "queue": queue,
                "status": str(cancelled_data.get("status") or "cancelled"),
                "canonical_status": state["canonical_status"],
                "active": state["active"],
                "terminal": state["terminal"],
                "failure_code": state["failure_code"],
            }
        )
    lifecycle = DEFAULT_KERNEL.lifecycle_summary(task_id)
    result["lifecycle"] = lifecycle
    catalog = result.get("catalog") if isinstance(result.get("catalog"), dict) else {}
    result["idempotency"] = {
        "request_fingerprint": catalog.get("request_fingerprint"),
        "attempt": catalog.get("attempt"),
        "max_attempts": catalog.get("max_attempts"),
        "retry_of": catalog.get("retry_of"),
        "root_task_id": catalog.get("root_task_id"),
        "retries": catalog.get("retries", []),
    }
    if lifecycle.get("cancel_request") and not result.get("terminal"):
        state = classify_task_state("cancel_requested")
        result.update(
            {
                "status": "cancel_requested",
                "canonical_status": state["canonical_status"],
                "active": state["active"],
                "terminal": state["terminal"],
                "failure_code": state["failure_code"],
            }
        )
    return result


def list_goals() -> dict[str, Any]:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for path in sorted(CATALOG_DIR.glob("*.json")):
        catalog = read_json(path)
        task_id = str(catalog.get("task_id") or "")
        current = task_status(task_id) if task_id else {}
        items.append(
            {
                "task_id": task_id or None,
                "project_key": catalog.get("project_key"),
                "status": current.get("status") or catalog.get("status"),
                "canonical_status": current.get("canonical_status"),
                "active": current.get("active"),
                "terminal": current.get("terminal"),
                "failure_code": current.get("failure_code"),
                "attempt": catalog.get("attempt"),
                "max_attempts": catalog.get("max_attempts"),
                "retry_of": catalog.get("retry_of"),
                "created_at": catalog.get("created_at"),
                "path": str(path),
            }
        )
    return {"catalog_dir": str(CATALOG_DIR), "items": items}


def cancel_goal(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")
    current = task_status(task_id)
    if current.get("terminal"):
        return {
            "task_id": task_id,
            "status": current.get("status"),
            "canonical_status": current.get("canonical_status"),
            "terminal": True,
            "idempotent": True,
        }
    lifecycle = current.get("lifecycle") if isinstance(current.get("lifecycle"), dict) else {}
    lease = lifecycle.get("lease") if isinstance(lifecycle.get("lease"), dict) else {}
    phase = str(lease.get("phase") or "")
    if phase in {"committing", "pushing"}:
        raise IntakeConflict(f"cancellation window closed during phase: {phase}")
    reason = str(payload.get("reason") or "operator_requested").strip()[:500]
    requested_by = str(payload.get("requested_by") or "web-console-operator").strip()[:200]
    result = DEFAULT_KERNEL.request_cancel(task_id, requested_by=requested_by, reason=reason)
    catalog_path = CATALOG_DIR / f"{task_id}.json"
    if catalog_path.exists():
        catalog = read_json(catalog_path)
        catalog["cancellation"] = result
        catalog["status"] = str(result.get("status") or catalog.get("status"))
        catalog["updated_at"] = now_iso()
        atomic_write_json(catalog_path, catalog)
    return {**result, "current_status": task_status(task_id)}


def existing_task_ids() -> set[str]:
    ids = {path.stem for path in CATALOG_DIR.glob("*.json")}
    for path in QUEUE_DIR.glob("*.json"):
        name = path.name
        for suffix in [".queued.json", ".running.json", ".done.json", ".failed.json", ".cancelled.json"]:
            if name.endswith(suffix):
                ids.add(name.removesuffix(suffix))
                break
    return ids


def retry_goal(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")
    current = task_status(task_id)
    if not current.get("terminal"):
        raise IntakeConflict("only terminal tasks can be retried")
    catalog_path = CATALOG_DIR / f"{task_id}.json"
    if not catalog_path.exists():
        raise TaskNotFound(f"task catalog not found: {task_id}")
    catalog = read_json(catalog_path)
    attempt = int(catalog.get("attempt") or 1) + 1
    max_attempts = int(payload.get("max_attempts") or catalog.get("max_attempts") or 3)
    if attempt > max_attempts:
        raise IntakeConflict(f"retry limit reached: attempt {attempt} exceeds max_attempts {max_attempts}")

    latest_retry = str(catalog.get("latest_retry_task_id") or "")
    if latest_retry and not payload.get("force_new_retry"):
        latest_path = CATALOG_DIR / f"{latest_retry}.json"
        if latest_path.exists():
            latest_status = task_status(latest_retry)
            if not latest_status.get("terminal"):
                replay = read_json(latest_path)
                replay["idempotent_replay"] = True
                replay["current_status"] = latest_status
                return replay

    requested_id = str(payload.get("new_task_id") or "").strip()
    new_task_id = requested_id or generate_retry_task_id(task_id, existing_task_ids())
    if not TASK_ID_RE.match(new_task_id):
        raise ValueError("invalid new_task_id")
    retry_payload = {
        "task_id": new_task_id,
        "project_key": catalog["project_key"],
        "objective": catalog["objective"],
        "constraints": catalog.get("constraints", []),
        "expected_checks": catalog.get("expected_checks", []),
        "commit_message": str(payload.get("commit_message") or catalog.get("commit_message") or ""),
        "notes": list(catalog.get("notes") or []) + [f"Explicit retry of {task_id}."],
        "retry_of": task_id,
        "root_task_id": catalog.get("root_task_id") or task_id,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "lease_seconds": int(payload.get("lease_seconds") or catalog.get("lease_seconds") or 60),
        "execution_timeout_seconds": int(
            payload.get("execution_timeout_seconds") or catalog.get("execution_timeout_seconds") or 7200
        ),
    }
    created = create_goal(retry_payload)
    retries = list(catalog.get("retries") or [])
    retries.append(
        {
            "task_id": new_task_id,
            "attempt": attempt,
            "created_at": now_iso(),
            "reason": str(payload.get("reason") or "explicit_retry")[:500],
        }
    )
    catalog["retries"] = retries
    catalog["latest_retry_task_id"] = new_task_id
    catalog["updated_at"] = now_iso()
    atomic_write_json(catalog_path, catalog)
    DEFAULT_KERNEL.append_event(
        task_id,
        "retry_created",
        status="completed" if current.get("canonical_status") == "completed" else current.get("canonical_status"),
        actor=str(payload.get("requested_by") or "web-console-operator")[:200],
        details={"retry_task_id": new_task_id, "attempt": attempt, "max_attempts": max_attempts},
    )
    return created


def read_body(handler: BaseHTTPRequestHandler, max_length: int = 80_000) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length == 0:
        return {}
    if length < 0 or length > max_length:
        raise ValueError("invalid_body_length")
    payload = json.loads(handler.rfile.read(length).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("body must be a JSON object")
    return payload


def error_response(handler: BaseHTTPRequestHandler, exc: Exception) -> None:
    if isinstance(exc, (TaskConflict, IntakeConflict)):
        status = 409
    elif isinstance(exc, (TaskNotFound, KeyError, FileNotFoundError)):
        status = 404
    else:
        status = 400
    json_response(handler, status, {"error": type(exc).__name__, "message": str(exc)})


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-intake/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            return json_response(
                self,
                200,
                {
                    "status": "ok",
                    "service": "dev_employee_intake_api_v2",
                    "queue_kernel": "transactional-filesystem-v1",
                },
            )
        if path == "/projects":
            return json_response(self, 200, {"projects": sorted(v1.registry().get("projects", {}).keys())})
        if path == "/goals":
            return json_response(self, 200, list_goals())
        if path.startswith("/goals/"):
            task_id = unquote(path.removeprefix("/goals/")).strip()
            try:
                return json_response(self, 200, task_status(task_id))
            except Exception as exc:
                return error_response(self, exc)
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not v1.auth_ok(self):
            return json_response(self, 401, {"error": "unauthorized"})
        try:
            if path == "/goals":
                result = create_goal(read_body(self))
                status = 200 if result.get("idempotent_replay") else (201 if result.get("status") == "queued" else 502)
                return json_response(self, status, result)
            if path.startswith("/goals/") and path.endswith("/cancel"):
                task_id = unquote(path.removeprefix("/goals/").removesuffix("/cancel")).strip("/")
                return json_response(self, 202, cancel_goal(task_id, read_body(self, max_length=20_000)))
            if path.startswith("/goals/") and path.endswith("/retry"):
                task_id = unquote(path.removeprefix("/goals/").removesuffix("/retry")).strip("/")
                result = retry_goal(task_id, read_body(self, max_length=20_000))
                status = 200 if result.get("idempotent_replay") else 201
                return json_response(self, status, result)
            return json_response(self, 404, {"error": "not_found"})
        except Exception as exc:
            return error_response(self, exc)


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS intake API v2 listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
