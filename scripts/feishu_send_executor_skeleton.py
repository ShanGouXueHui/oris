#!/usr/bin/env python3
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from scripts.lib.runtime_config import local_service_url, rel_path, read_oris_api_key, exact_reply_patterns, role_routing, read_feishu_creds, feishu_api, default_source

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = rel_path("feishu_send_executor_log")

TOKEN_URL = feishu_api("token_url")
SEND_URL = feishu_api("send_url")
REPLY_URL_TEMPLATE = feishu_api("reply_url_template")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def append_jsonl(path: Path, record: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 120):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_tenant_access_token(app_id: str, app_secret: str):
    payload = {
        "app_id": app_id,
        "app_secret": app_secret,
    }
    resp = post_json(TOKEN_URL, payload)
    token = resp.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"tenant_access_token missing: {resp}")
    return token, resp

def build_execute_request(send_envelope: dict):
    reply_to = send_envelope.get("reply_to_message_id")
    msg_type = send_envelope.get("msg_type", "text")
    content = send_envelope.get("content") or {}
    receive_id_type = send_envelope.get("receive_id_type", "chat_id")
    receive_id = send_envelope.get("receive_id")

    if reply_to:
        url = REPLY_URL_TEMPLATE.format(message_id=reply_to)
        payload = {
            "content": json.dumps(content, ensure_ascii=False),
            "msg_type": msg_type,
        }
        mode = "reply"
    else:
        if not receive_id:
            raise RuntimeError("send_envelope missing receive_id for send mode")
        url = f"{SEND_URL}?receive_id_type={receive_id_type}"
        payload = {
            "receive_id": receive_id,
            "content": json.dumps(content, ensure_ascii=False),
            "msg_type": msg_type,
        }
        mode = "send"

    return mode, url, payload

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transport-preview-file", default=None)
    ap.add_argument("--transport-preview-json", default=None)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    if args.transport_preview_file:
        preview = load_json(Path(args.transport_preview_file), {})
    elif args.transport_preview_json and args.transport_preview_json.strip():
        preview = json.loads(args.transport_preview_json)
    else:
        raise SystemExit("either --transport-preview-file or --transport-preview-json is required")

    send_envelope = preview.get("send_envelope") or {}
    identity = preview.get("identity") or {}
    dedupe_key = preview.get("dedupe_key")
    mode_in = preview.get("mode")

    if mode_in == "deduped":
        out = {
            "ok": True,
            "mode": "skipped_deduped",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "reason": "transport input was deduped; no send should happen",
        }
        append_jsonl(LOG_PATH, {
            "ts": utc_now(),
            "mode": "skipped_deduped",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "ok": True,
        })
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if not send_envelope:
        out = {
            "ok": False,
            "mode": "invalid_input",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "error": "missing send_envelope",
        }
        append_jsonl(LOG_PATH, {
            "ts": utc_now(),
            "mode": "invalid_input",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "ok": False,
            "error": "missing send_envelope",
        })
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    app_id, app_secret = read_feishu_creds()
    if not app_id or not app_secret:
        raise SystemExit("missing feishu appId/appSecret from ~/.openclaw/openclaw.json or ~/.openclaw/secrets.json")

    token, token_resp = fetch_tenant_access_token(app_id, app_secret)
    mode, url, payload = build_execute_request(send_envelope)

    record = {
        "ts": utc_now(),
        "mode": mode,
        "identity": identity,
        "dedupe_key": dedupe_key,
        "execute": bool(args.execute),
        "send_envelope": send_envelope,
        "request_url": url,
        "request_payload": payload,
    }

    if not args.execute:
        record["ok"] = True
        record["dry_run"] = True
        append_jsonl(LOG_PATH, record)
        print(json.dumps({
            "ok": True,
            "mode": "dry_run",
            "identity": identity,
            "dedupe_key": dedupe_key,
            "token_status": {
                "ok": True,
                "has_tenant_access_token": bool(token),
                "expire": token_resp.get("expire"),
            },
            "send_request_preview": {
                "mode": mode,
                "url": url,
                "payload": payload,
            }
        }, ensure_ascii=False, indent=2))
        return

    headers = {
        "Authorization": f"Bearer {token}",
    }
    send_resp = post_json(url, payload, headers=headers)

    record["ok"] = True
    record["dry_run"] = False
    record["send_response"] = send_resp
    append_jsonl(LOG_PATH, record)

    print(json.dumps({
        "ok": True,
        "mode": "executed",
        "identity": identity,
        "dedupe_key": dedupe_key,
        "token_status": {
            "ok": True,
            "has_tenant_access_token": bool(token),
            "expire": token_resp.get("expire"),
        },
        "send_result": send_resp,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
