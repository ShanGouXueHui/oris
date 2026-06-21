#!/usr/bin/env python3
"""Read ORIS Dev Employee task status from the local enqueue/status API."""

from __future__ import annotations

import argparse
import json
import urllib.error as urlerror
import urllib.parse as urlparse
import urllib.request as urlrequest

from dev_employee_runtime.net import require_loopback_url
from dev_employee_runtime.paths import discover_repo_root
from dev_employee_runtime.settings import load_runtime_settings


def default_base_url() -> str:
    return load_runtime_settings(discover_repo_root()).queue_url


def fetch_json(url: str) -> tuple[int, object]:
    try:
        with urlrequest.urlopen(url, timeout=20) as resp:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Read local ORIS Dev Employee task status")
    parser.add_argument("--task-id")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--queue", action="store_true")
    parser.add_argument("--base-url", default=default_base_url())
    args = parser.parse_args()

    require_loopback_url(args.base_url)
    base = args.base_url.rstrip("/")
    if args.queue:
        path = "/queue"
    elif args.latest:
        path = "/latest"
    elif args.task_id:
        path = "/task/" + urlparse.quote(args.task_id, safe="")
    else:
        raise SystemExit("ERROR: choose --queue, --latest or --task-id")
    status, payload = fetch_json(base + path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
