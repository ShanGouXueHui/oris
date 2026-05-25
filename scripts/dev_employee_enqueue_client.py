#!/usr/bin/env python3
"""Submit one ORIS Dev Employee task to the local loopback enqueue API.

This is a narrow client wrapper. It does not execute shell commands, does not
invoke Codex, and does not perform Git operations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
DEFAULT_URL = "http://127.0.0.1:18891/enqueue"
QUEUE_KEY_NAME = "ORIS_DEV_EMPLOYEE_ENQUEUE_" + "TOKEN"
HEADER_NAME = "X-ORIS-" + "Token"


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


def post_json(url: str, auth_value: str, payload: dict[str, Any]) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            HEADER_NAME: auth_value,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except urllib.error.URLError as exc:
        return 599, json.dumps({"error": "url_error", "message": str(exc)}, ensure_ascii=False)


def parse_response(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def main() -> int:
    parser = argparse.ArgumentParser(description="Enqueue an ORIS Dev Employee task through the local API")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--prompt-path", required=True)
    parser.add_argument("--product-path", required=True)
    parser.add_argument("--product-repo", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--note", default="Queued by dev_employee_enqueue_client.py")
    parser.add_argument("--url", default=os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_URL", DEFAULT_URL))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    args = parser.parse_args()

    if not args.url.startswith("http://127.0.0.1:") and not args.url.startswith("http://localhost:"):
        raise SystemExit("ERROR: refusing non-loopback enqueue URL")

    env = load_env(Path(args.env_file))
    auth_value = env.get(QUEUE_KEY_NAME)
    if not auth_value:
        raise SystemExit(f"ERROR: {QUEUE_KEY_NAME} missing from env file")

    payload = {
        "task_id": args.task_id,
        "prompt_path": args.prompt_path,
        "product_path": args.product_path,
        "product_repo": args.product_repo,
        "commit_message": args.commit_message,
        "note": args.note,
    }
    status, response_text = post_json(args.url, auth_value, payload)
    output = {"http_status": status, "response": parse_response(response_text)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
