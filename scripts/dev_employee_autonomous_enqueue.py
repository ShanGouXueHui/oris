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
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
BASE_TEMPLATE = ORIS_DIR / "prompts" / "dev_employee_autonomous_development_task_template_20260526.md"
RUNTIME_PROMPT_DIR = ORIS_DIR / "run" / "dev_employee_prompts"
DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
DEFAULT_URL = "http://127.0.0.1:18891/enqueue"
AUTH_KEY = "ORIS_DEV_EMPLOYEE_ENQUEUE_" + "TOKEN"
AUTH_HEADER = "X-ORIS-" + "Token"


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"ERROR: env file not found: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


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
    if not url.startswith("http://127.0.0.1:") and not url.startswith("http://localhost:"):
        raise SystemExit("ERROR: refusing non-loopback enqueue URL")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", AUTH_HEADER: auth_value},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except urllib.error.URLError as exc:
        return 599, json.dumps({"error": "url_error", "message": str(exc)}, ensure_ascii=False)


def parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and enqueue an autonomous ORIS Dev Employee task")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--product-path", required=True)
    parser.add_argument("--product-repo", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--note", default="Queued by dev_employee_autonomous_enqueue.py")
    parser.add_argument("--url", default=os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_URL", DEFAULT_URL))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    args = parser.parse_args()

    env = load_env(Path(args.env_file))
    auth_value = env.get(AUTH_KEY)
    if not auth_value:
        raise SystemExit(f"ERROR: {AUTH_KEY} missing from env file")

    prompt_path = write_runtime_prompt(args.task_id, args.objective, args.constraint, args.check)
    payload = {
        "task_id": args.task_id,
        "prompt_path": str(prompt_path),
        "product_path": args.product_path,
        "product_repo": args.product_repo,
        "commit_message": args.commit_message,
        "note": args.note,
        "strict_result_schema": True,
        "task_objective": args.objective,
        "constraints": args.constraint,
    }
    status, response_text = post_json(args.url, auth_value, payload)
    output = {"http_status": status, "runtime_prompt_path": str(prompt_path), "response": parse_json(response_text)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
