#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SCRIPT = ROOT / "scripts" / "bridge_feishu_to_oris.py"
LOG_PATH = ROOT / "orchestration" / "feishu_event_ingress_log.jsonl"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path: Path, record: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def load_payload(args):
    if args.payload_file:
        return json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    raw = args.payload_json or ""
    if raw.strip():
        return json.loads(raw)
    raise SystemExit("either --payload-file or --payload-json is required")

def parse_text_message(payload: dict):
    header = payload.get("header") or {}
    event_type = header.get("event_type")

    if event_type != "im.message.receive_v1":
        return None

    event = payload.get("event") or {}
    sender = (((event.get("sender") or {}).get("sender_id") or {}).get("open_id"))
    message = event.get("message") or {}
    chat_id = message.get("chat_id")
    message_id = message.get("message_id")
    message_type = message.get("message_type")
    content_raw = message.get("content") or "{}"

    try:
        content = json.loads(content_raw)
    except Exception:
        content = {}

    text = content.get("text", "")

    return {
        "event_type": event_type,
        "sender_open_id": sender,
        "chat_id": chat_id,
        "message_id": message_id,
        "message_type": message_type,
        "text": text,
    }

def run_bridge(sender_open_id: str, chat_id: str, text: str):
    cmd = [
        "/usr/bin/python3",
        str(BRIDGE_SCRIPT),
        "--sender-open-id", sender_open_id,
        "--chat-id", chat_id,
        "--text", text,
        "--source", "feishu_event_ingress",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "bridge_failed")
    return json.loads(result.stdout)

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

    parsed = parse_text_message(payload)
    if not parsed:
        out = {
            "ok": False,
            "error": "unsupported_event_type",
            "event_type": ((payload.get("header") or {}).get("event_type")),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    record = {
        "ts": utc_now(),
        "event_type": parsed.get("event_type"),
        "sender_open_id": parsed.get("sender_open_id"),
        "chat_id": parsed.get("chat_id"),
        "message_id": parsed.get("message_id"),
        "message_type": parsed.get("message_type"),
        "text_preview": (parsed.get("text") or "")[:300],
    }

    try:
        bridge_result = run_bridge(
            sender_open_id=parsed["sender_open_id"],
            chat_id=parsed["chat_id"],
            text=parsed["text"],
        )
        reply_text = bridge_result.get("reply_text", "").strip()

        out = {
            "ok": True,
            "mode": "message_reply_preview",
            "ingress": parsed,
            "reply_action": {
                "type": "text",
                "message_id": parsed.get("message_id"),
                "chat_id": parsed.get("chat_id"),
                "text": reply_text,
            },
            "bridge_result": bridge_result,
        }

        record["ok"] = True
        record["reply_text_preview"] = reply_text[:300]
        record["bridge_result"] = bridge_result
        append_jsonl(LOG_PATH, record)

        print(json.dumps(out, ensure_ascii=False, indent=2))

    except Exception as e:
        record["ok"] = False
        record["error"] = f"{type(e).__name__}: {e}"
        append_jsonl(LOG_PATH, record)
        print(json.dumps({
            "ok": False,
            "mode": "message_reply_preview",
            "ingress": parsed,
            "error": f"{type(e).__name__}: {e}",
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)

if __name__ == "__main__":
    main()
