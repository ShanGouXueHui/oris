from __future__ import annotations

import json
import os
import urllib.error as urlerror
import urllib.request as urlrequest
from pathlib import Path
from typing import Any

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.json_store import atomic_write_json, read_json
from dev_employee_runtime.net import require_loopback_url
from dev_employee_runtime.intake_config import (
    AUTH_HEADER,
    BASE_TEMPLATE,
    CATALOG_DIR,
    DEFAULT_ENQUEUE_URL,
    RUNTIME_PROMPT_DIR,
    TASK_ID_RE,
    default_task_id,
    enqueue_token,
    resolve_project,
    sanitize_list,
)


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
    require_loopback_url(url)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", AUTH_HEADER: enqueue_token()},
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text)
    except urlerror.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(text)
        except json.JSONDecodeError:
            return exc.code, {"raw": text}
    except urlerror.URLError as exc:
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
    atomic_write_json(path, data)
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
    atomic_write_json(CATALOG_DIR / f"{task_id}.json", catalog)
    return catalog
