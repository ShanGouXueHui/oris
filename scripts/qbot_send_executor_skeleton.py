#!/usr/bin/env python3
import argparse
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "orchestration" / "qbot_send_executor_log.jsonl"
RUNTIME_PATH = ROOT / "config" / "report_runtime.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    p = Path(path)
    if not p.is_file():
        return {} if default is None else default
    return json.loads(p.read_text(encoding="utf-8"))

def append_jsonl(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def runtime_qbot():
    cfg = load_json(RUNTIME_PATH, {})
    return ((cfg.get("channels") or {}).get("qbot")) or {}

def post_json(url, payload, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "oris-qbot-send-executor/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = raw
        return resp.getcode(), body

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transport-preview-file", default=None)
    ap.add_argument("--transport-preview-json", default=None)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    if args.transport_preview_file:
        preview = load_json(args.transport_preview_file, {})
    elif args.transport_preview_json and args.transport_preview_json.strip():
        preview = json.loads(args.transport_preview_json)
    else:
        raise SystemExit("either --transport-preview-file or --transport-preview-json is required")

    send_envelope = preview.get("send_envelope") or {}
    identity = preview.get("identity") or {}
    dedupe_key = preview.get("dedupe_key")

    qbot_cfg = runtime_qbot()
    env_name = qbot_cfg.get("webhook_url_env", "QBOT_WEBHOOK_URL")
    execute_enabled = bool(qbot_cfg.get("execute_enabled", False))

    text = ((send_envelope.get("content") or {}).get("text")) or ""
    target = send_envelope.get("target")
    webhook_url = target or os.environ.get(env_name) or qbot_cfg.get("webhook_url")
    request_payload = {"content": text}

    record = {
        "ts": utc_now(),
        "mode": "send",
        "identity": identity,
        "dedupe_key": dedupe_key,
        "execute": bool(args.execute),
        "execute_enabled": execute_enabled,
        "webhook_present": bool(webhook_url),
        "request_payload": request_payload,
    }

    if not args.execute:
        record["ok"] = True
        record["dry_run"] = True
        record["request_url"] = webhook_url
        append_jsonl(LOG_PATH, record)
        print(json.dumps({
            "ok": True,
            "mode": "dry_run",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "config_status": {
                "execute_enabled": execute_enabled,
                "webhook_present": bool(webhook_url),
                "webhook_env_name": env_name,
            },
            "send_request_preview": {
                "url": webhook_url,
                "payload": request_payload,
            }
        }, ensure_ascii=False, indent=2))
        return

    if not execute_enabled:
        out = {
            "ok": False,
            "mode": "channel_disabled",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "error": "qbot execute disabled in config/report_runtime.json",
        }
        record["ok"] = False
        record["error"] = out["error"]
        append_jsonl(LOG_PATH, record)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    if not webhook_url:
        out = {
            "ok": False,
            "mode": "missing_webhook",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "error": f"missing qbot webhook url from target or env {env_name}",
        }
        record["ok"] = False
        record["error"] = out["error"]
        append_jsonl(LOG_PATH, record)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    try:
        status_code, body = post_json(webhook_url, request_payload)
        out = {
            "ok": 200 <= status_code < 300,
            "mode": "executed",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "status_code": status_code,
            "send_result": body,
        }
        record["ok"] = out["ok"]
        record["dry_run"] = False
        record["request_url"] = webhook_url
        record["status_code"] = status_code
        record["send_response"] = body
        append_jsonl(LOG_PATH, record)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        if not out["ok"]:
            raise SystemExit(2)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = str(e)
        out = {
            "ok": False,
            "mode": "http_error",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "status_code": e.code,
            "error": body,
        }
        record["ok"] = False
        record["request_url"] = webhook_url
        record["status_code"] = e.code
        record["error"] = body
        append_jsonl(LOG_PATH, record)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    except Exception as e:
        out = {
            "ok": False,
            "mode": "exception",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "error": f"{type(e).__name__}: {e}",
        }
        record["ok"] = False
        record["request_url"] = webhook_url
        record["error"] = out["error"]
        append_jsonl(LOG_PATH, record)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(2)

if __name__ == "__main__":
    main()
