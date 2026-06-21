#!/usr/bin/env python3
"""Submit one ORIS Dev Employee task to the local loopback enqueue API.

This narrow client wrapper does not execute shell commands, invoke Codex, or
perform Git operations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error as urlerror
import urllib.request as urlrequest
from pathlib import Path
from typing import Any

from dev_employee_runtime.env import load_env
from dev_employee_runtime.http import parse_json_response
from dev_employee_runtime.net import require_loopback_url
from dev_employee_runtime.settings import load_runtime_settings
from dev_employee_runtime.paths import discover_repo_root

DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
QUEUE_KEY_NAME = "ORIS_DEV_EMPLOYEE_ENQUEUE_" + "TOKEN"
HEADER_NAME = "X-ORIS-" + "Token"


def default_enqueue_url() -> str:
    value = os.environ.get("ORIS_DEV_EMPLOYEE_ENQUEUE_URL")
    if value:
        return value
    settings = load_runtime_settings(discover_repo_root())
    return f"{settings.queue_url}/enqueue"


def post_json(url: str, auth_value: str, payload: dict[str, Any]) -> tuple[int, str]:
    require_loopback_url(url)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", HEADER_NAME: auth_value},
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except urlerror.URLError as exc:
        return 599, json.dumps({"error": "url_error", "message": str(exc)}, ensure_ascii=False)


def parse_response(text: str) -> Any:
    return parse_json_response(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enqueue an ORIS Dev Employee task through the local API")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--prompt-path", required=True)
    parser.add_argument("--product-path", required=True)
    parser.add_argument("--product-repo", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--note", default="Queued by dev_employee_enqueue_client.py")
    parser.add_argument("--url", default=default_enqueue_url())
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    args = parser.parse_args()

    require_loopback_url(args.url)
    env = load_env(Path(args.env_file))
    token = os.environ.get(QUEUE_KEY_NAME) or env.get(QUEUE_KEY_NAME)
    if not token:
        raise SystemExit(f"ERROR: missing {QUEUE_KEY_NAME} in environment or {args.env_file}")

    payload = {
        "task_id": args.task_id,
        "prompt_path": args.prompt_path,
        "product_path": args.product_path,
        "product_repo": args.product_repo,
        "commit_message": args.commit_message,
        "note": args.note,
    }
    status, text = post_json(args.url, token, payload)
    print(json.dumps(parse_response(text), ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
