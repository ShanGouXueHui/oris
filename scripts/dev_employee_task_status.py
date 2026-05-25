#!/usr/bin/env python3
"""Read ORIS Dev Employee task status from the local enqueue/status API."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:18891"


def fetch_json(url: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Read local ORIS Dev Employee task status")
    parser.add_argument("--task-id")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--queue", action="store_true")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    if not args.base_url.startswith("http://127.0.0.1:") and not args.base_url.startswith("http://localhost:"):
        raise SystemExit("ERROR: refusing non-loopback status URL")

    if args.task_id:
        path = "/task/" + urllib.parse.quote(args.task_id, safe="")
    elif args.queue:
        path = "/queue"
    else:
        path = "/latest"

    status, payload = fetch_json(args.base_url.rstrip("/") + path)
    print(json.dumps({"http_status": status, "response": payload}, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
