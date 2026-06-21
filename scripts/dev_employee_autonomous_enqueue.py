#!/usr/bin/env python3
"""Create and enqueue an autonomous ORIS Dev Employee development task.

Human supplies goal and constraints. This helper creates a local runtime prompt
under run/dev_employee_prompts/ and submits it to the local enqueue API. It does
not execute shell commands, invoke Codex, or perform Git operations.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error as urlerror
import urllib.request as urlrequest
from pathlib import Path
from typing import Any

from dev_employee_runtime.env import load_env
from dev_employee_runtime.http import parse_json_response
from dev_employee_runtime.net import require_loopback_url
from dev_employee_runtime.paths import discover_repo_root
from dev_employee_runtime.settings import load_runtime_settings

ORIS_DIR = discover_repo_root()
BASE_TEMPLATE = ORIS_DIR / "prompts" / "dev_employee_autonomous_development_task_template_20260526.md"
RUNTIME_PROMPT_DIR = ORIS_DIR / "run" / "dev_employee_prompts"
DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
AUTH_KEY = "ORIS_DEV_EMPLOYEE_ENQUEUE_" + "TOKEN"
AUTH_HEADER = "X-ORIS-" + "Token"


def default_enqueue_url() -> str:
    value = os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_URL")
    if value:
        return value
    return f"{load_runtime_settings(ORIS_DIR).queue_url}/enqueue"


def write_runtime_prompt(task_id: str, objective: str, constraints: list[str], checks: list[str]) -> Path:
    if not BASE_TEMPLATE.exists():
        raise SystemExit(f"ERROR: base template not found: {BASE_TEMPLATE}")
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
        + "## Human constraints\n\n"
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


def post_json(url: str, auth_value: str, payload: dict[str, Any]) -> tuple[int, str]:
    require_loopback_url(url)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", AUTH_HEADER: auth_value},
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except urlerror.URLError as exc:
        return 599, json.dumps({"error": "url_error", "message": str(exc)}, ensure_ascii=False)


def csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";;") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and enqueue an autonomous ORIS Dev Employee task")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--constraints", help="Optional ';;' separated constraints")
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--expected-checks", help="Optional ';;' separated expected checks")
    parser.add_argument("--product-path", required=True)
    parser.add_argument("--product-repo", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--note", default="Queued by dev_employee_autonomous_enqueue.py")
    parser.add_argument("--url", default=default_enqueue_url())
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    args = parser.parse_args()

    require_loopback_url(args.url)
    env = load_env(Path(args.env_file))
    token = os.environ.get(AUTH_KEY) or env.get(AUTH_KEY)
    if not token:
        raise SystemExit(f"ERROR: missing {AUTH_KEY} in environment or {args.env_file}")

    constraints = [*args.constraint, *csv_list(args.constraints)]
    checks = [*args.check, *csv_list(args.expected_checks)]
    prompt_path = write_runtime_prompt(args.task_id, args.objective, constraints, checks)
    payload = {
        "task_id": args.task_id,
        "prompt_path": str(prompt_path),
        "product_path": args.product_path,
        "product_repo": args.product_repo,
        "commit_message": args.commit_message,
        "note": args.note,
        "strict_result_schema": True,
        "task_objective": args.objective,
        "constraints": constraints,
        "expected_checks": checks,
    }
    status, text = post_json(args.url, token, payload)
    print(json.dumps(parse_json_response(text), ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
