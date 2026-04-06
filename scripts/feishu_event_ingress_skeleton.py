#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.runtime_config import rel_path, default_source

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = rel_path("feishu_ingress_log")
BRIDGE_SCRIPT = ROOT / "scripts" / "bridge_feishu_to_oris.py"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path, record):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def load_payload(args):
    if args.payload_json:
        return json.loads(args.payload_json)
    if args.payload_file:
        return json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    raise SystemExit("missing --payload-json or --payload-file")

def parse_text_content(message_type, content):
    if message_type == "text":
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return (parsed.get("text") or "").strip()
            except Exception:
                return content.strip()
        if isinstance(content, dict):
            return (content.get("text") or "").strip()
    return ""

def normalize_event(payload):
    # real Feishu schema 2.0
    header = payload.get("header") or {}
    event = payload.get("event") or {}

    if header or event:
        sender_open_id = (
            (((event.get("sender") or {}).get("sender_id") or {}).get("open_id"))
            or ""
        )
        message = event.get("message") or {}
        return {
            "event_type": header.get("event_type") or payload.get("type") or "",
            "event_id": header.get("event_id") or payload.get("event_id") or "",
            "sender_open_id": sender_open_id,
            "chat_id": message.get("chat_id") or "",
            "message_id": message.get("message_id") or "",
            "message_type": message.get("message_type") or "",
            "text": parse_text_content(message.get("message_type"), message.get("content")),
        }

    # flattened / test payload compatibility
    return {
        "event_type": payload.get("event_type") or payload.get("type") or "",
        "event_id": payload.get("event_id") or "",
        "sender_open_id": payload.get("sender_open_id") or "",
        "chat_id": payload.get("chat_id") or "",
        "message_id": payload.get("message_id") or "",
        "message_type": payload.get("message_type") or "",
        "text": (payload.get("text") or "").strip(),
    }

def call_bridge(sender_open_id, chat_id, text):
    cmd = [
        "/usr/bin/python3",
        str(BRIDGE_SCRIPT),
        "--sender-open-id", sender_open_id,
        "--chat-id", chat_id,
        "--text", text,
        "--source", default_source("feishu_ingress"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"bridge_failed rc={result.returncode} stderr={result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except Exception as e:
        raise RuntimeError(f"bridge_non_json: {e}; stdout={result.stdout[:1000]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload-json")
    ap.add_argument("--payload-file")
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

    ingress = normalize_event(payload)
    record = {
        "ts": utc_now(),
        "event_type": ingress.get("event_type"),
        "sender_open_id": ingress.get("sender_open_id"),
        "chat_id": ingress.get("chat_id"),
        "message_id": ingress.get("message_id"),
        "message_type": ingress.get("message_type"),
        "text_preview": (ingress.get("text") or "")[:300],
    }

    if ingress.get("message_type") != "text" or not ingress.get("text"):
        record["ok"] = True
        record["mode"] = "ignored_non_text_or_empty"
        append_jsonl(LOG_PATH, record)
        print(json.dumps({
            "ok": True,
            "mode": "ignored_non_text_or_empty",
            "ingress": ingress,
            "reply_action": None,
            "bridge_result": None,
        }, ensure_ascii=False, indent=2))
        return

    try:
        bridge_result = call_bridge(
            sender_open_id=ingress["sender_open_id"],
            chat_id=ingress["chat_id"],
            text=ingress["text"],
        )
        reply_text = (bridge_result.get("reply_text") or "").strip()

        out = {
            "ok": True,
            "mode": "message_reply_preview",
            "ingress": ingress,
            "reply_action": {
                "type": "text",
                "message_id": ingress["message_id"],
                "chat_id": ingress["chat_id"],
                "text": reply_text,
            },
            "bridge_result": bridge_result,
        }

        record["ok"] = True
        record["mode"] = "message_reply_preview"
        record["reply_text_preview"] = reply_text[:300]
        record["bridge_result"] = bridge_result
        append_jsonl(LOG_PATH, record)

        print(json.dumps(out, ensure_ascii=False, indent=2))

    except Exception as e:
        record["ok"] = False
        record["mode"] = "bridge_failed"
        record["error"] = f"{type(e).__name__}: {e}"
        append_jsonl(LOG_PATH, record)
        print(json.dumps({
            "ok": False,
            "mode": "bridge_failed",
            "ingress": ingress,
            "error": f"{type(e).__name__}: {e}",
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

if __name__ == "__main__":
    main()
