#!/usr/bin/env python3
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
LOG_PATH = ROOT / "orchestration" / "feishu_send_executor_log.jsonl"

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
REPLY_URL_TEMPLATE = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"

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

def deep_get(data, path):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

def read_feishu_creds():
    cfg = load_json(OPENCLAW_CONFIG_PATH, {})
    sec = load_json(SECRETS_PATH, {})

    app_id_candidates = [
        ["channels", "feishu", "accounts", "main", "appId"],
        ["channels", "feishu", "appId"],
    ]
    app_secret_candidates = [
        ["channels", "feishu", "accounts", "main", "appSecret"],
        ["channels", "feishu", "appSecret"],
        ["channels", "feishu", "accounts", "main", "app_secret"],
        ["channels", "feishu", "app_secret"],
    ]

    app_id = None
    for p in app_id_candidates:
        v = deep_get(cfg, p)
        if isinstance(v, str) and v.strip():
            app_id = v.strip()
            break
    if not app_id:
        for p in app_id_candidates:
            v = deep_get(sec, p)
            if isinstance(v, str) and v.strip():
                app_id = v.strip()
                break

    app_secret = None
    for p in app_secret_candidates:
        v = deep_get(sec, p)
        if isinstance(v, str) and v.strip():
            app_secret = v.strip()
            break

    return app_id, app_secret

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
