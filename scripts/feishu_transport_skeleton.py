#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INGRESS_SCRIPT = ROOT / "scripts" / "feishu_event_ingress_skeleton.py"
DEDUPE_PATH = ROOT / "orchestration" / "feishu_event_dedupe.json"
LOG_PATH = ROOT / "orchestration" / "feishu_transport_log.jsonl"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def append_jsonl(path: Path, record: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def load_payload(args):
    if args.payload_file:
        return json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    if args.payload_json and args.payload_json.strip():
        return json.loads(args.payload_json)
    raise SystemExit("either --payload-file or --payload-json is required")

def event_identity(payload: dict):
    header = payload.get("header") or {}
    event = payload.get("event") or {}
    message = event.get("message") or {}

    return {
        "event_type": header.get("event_type"),
        "event_id": header.get("event_id"),
        "message_id": message.get("message_id"),
        "chat_id": message.get("chat_id"),
    }

def dedupe_key(identity: dict):
    if identity.get("event_id"):
        return f"event:{identity['event_id']}"
    if identity.get("message_id"):
        return f"message:{identity['message_id']}"
    return None

def run_ingress(payload: dict):
    cmd = [
        "/usr/bin/python3",
        str(INGRESS_SCRIPT),
        "--payload-json",
        json.dumps(payload, ensure_ascii=False),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ingress_failed")
    return json.loads(result.stdout)

def build_send_envelope(preview: dict):
    reply_action = preview.get("reply_action") or {}
    text = reply_action.get("text", "").strip()
    chat_id = reply_action.get("chat_id")
    message_id = reply_action.get("message_id")

    return {
        "send_mode": "feishu_messages_api_preview",
        "endpoint_hint": "/open-apis/im/v1/messages",
        "receive_id_type": "chat_id",
        "receive_id": chat_id,
        "reply_to_message_id": message_id,
        "msg_type": "text",
        "content": {
            "text": text
        }
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload-file", default=None)
    ap.add_argument("--payload-json", default=None)
    args = ap.parse_args()

    payload = load_payload(args)

    if "challenge" in payload:
        out = {
            "ok": True,
            "mode": "challenge",
            "challenge": payload.get("challenge"),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    identity = event_identity(payload)
    key = dedupe_key(identity)

    dedupe = load_json(DEDUPE_PATH, {"version": 1, "updated_at": None, "seen": {}})
    seen = dedupe.setdefault("seen", {})

    if key and key in seen:
        out = {
            "ok": True,
            "mode": "deduped",
            "identity": identity,
            "dedupe_key": key,
            "first_seen_at": seen[key],
        }
        append_jsonl(LOG_PATH, {
            "ts": utc_now(),
            "mode": "deduped",
            "identity": identity,
            "dedupe_key": key,
            "first_seen_at": seen[key],
        })
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    preview = run_ingress(payload)
    if not preview.get("ok"):
        append_jsonl(LOG_PATH, {
            "ts": utc_now(),
            "mode": "ingress_failed",
            "identity": identity,
            "preview": preview,
        })
        print(json.dumps({
            "ok": False,
            "mode": "transport_preview",
            "identity": identity,
            "preview": preview,
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    send_envelope = build_send_envelope(preview)

    if key:
        seen[key] = utc_now()
        dedupe["updated_at"] = utc_now()
        save_json(DEDUPE_PATH, dedupe)

    out = {
        "ok": True,
        "mode": "transport_preview",
        "identity": identity,
        "dedupe_key": key,
        "send_envelope": send_envelope,
        "preview": preview,
    }

    append_jsonl(LOG_PATH, {
        "ts": utc_now(),
        "mode": "transport_preview",
        "identity": identity,
        "dedupe_key": key,
        "send_envelope": send_envelope,
    })

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
