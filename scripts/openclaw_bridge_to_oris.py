#!/usr/bin/env python3
import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from scripts.lib.runtime_config import local_service_url, rel_path, read_oris_api_key, exact_reply_patterns, role_routing, read_feishu_creds, feishu_api, default_source
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = rel_path("openclaw_bridge_log")
LOCAL_V1_INFER_URL = local_service_url("oris_v1_infer_url")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def append_jsonl(path: Path, record: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def choose_role(text: str) -> str:
    t = (text or "").strip().lower()
    routing = role_routing()
    coding_keywords = routing.get("coding_keywords", [])
    report_keywords = routing.get("report_keywords", [])
    cn_keywords = routing.get("cn_keywords", [])
    cheap_keywords = routing.get("cheap_keywords", [])

    if any(k in t for k in coding_keywords):
        return "coding"
    if any(k in t for k in report_keywords):
        return "report_generation"
    if any(k in t for k in cn_keywords):
        return "cn_candidate_pool"
    if any(k in t for k in cheap_keywords):
        return "free_fallback"
    return "primary_general"

def apply_reply_policy(input_text: str, raw_reply: str) -> tuple[str, str]:
    text = (input_text or "").strip()
    reply = (raw_reply or "").strip()

    patterns = exact_reply_patterns()

    for p in patterns:
        m = re.match(p, text, flags=re.IGNORECASE)
        if m:
            forced = m.group(1).strip()
            forced = forced.strip('“”"\' ')
            return forced, "exact_reply_rule"

    return reply, "model_raw"

def call_oris(role: str, prompt: str, source: str, request_id: str, api_key: str):
    payload = {
        "role": role,
        "prompt": prompt,
        "source": source,
        "request_id": request_id,
    }
    req = urllib.request.Request(
        LOCAL_V1_INFER_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-ORIS-API-Key": api_key,
            "User-Agent": "ORIS-OpenClaw-Bridge/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-id", required=True)
    ap.add_argument("--user-id", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--role", default=None)
    ap.add_argument("--source", default=default_source("openclaw_bridge"))
    args = ap.parse_args()

    api_key = read_oris_api_key()
    if not api_key:
        raise SystemExit("missing ORIS API key in ~/.openclaw/secrets.json")

    request_id = str(uuid.uuid4())
    role = args.role or choose_role(args.text)

    record = {
        "ts": utc_now(),
        "request_id": request_id,
        "source": args.source,
        "session_id": args.session_id,
        "user_id": args.user_id,
        "input_text_preview": args.text[:300],
        "selected_role": role,
    }

    try:
        result = call_oris(role=role, prompt=args.text, source=args.source, request_id=request_id, api_key=api_key)
        raw_reply = (((result.get("data") or {}).get("text")) or "").strip()
        reply_text, reply_policy = apply_reply_policy(args.text, raw_reply)

        record["ok"] = bool(result.get("ok"))
        record["reply_policy"] = reply_policy
        record["oris_response"] = result
        record["reply_text_preview"] = reply_text[:300]
        append_jsonl(LOG_PATH, record)

        print(json.dumps({
            "ok": bool(result.get("ok")),
            "request_id": request_id,
            "bridge": {
                "channel": "openclaw",
                "session_id": args.session_id,
                "user_id": args.user_id,
                "selected_role": role,
                "reply_policy": reply_policy,
            },
            "reply_text": reply_text,
            "oris_result": result,
        }, ensure_ascii=False, indent=2))

    except Exception as e:
        record["ok"] = False
        record["error"] = f"{type(e).__name__}: {e}"
        append_jsonl(LOG_PATH, record)
        print(json.dumps({
            "ok": False,
            "request_id": request_id,
            "bridge": {
                "channel": "openclaw",
                "session_id": args.session_id,
                "user_id": args.user_id,
                "selected_role": role,
            },
            "error": f"{type(e).__name__}: {e}",
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)

if __name__ == "__main__":
    main()
