#!/usr/bin/env python3
import argparse
import json
import re
import urllib.request
import uuid
from datetime import datetime, timezone

from lib.runtime_config import (
    local_service_url,
    rel_path,
    read_oris_api_key,
    role_routing,
    exact_reply_patterns,
    default_source,
    config,
)

CFG = config()
LOG_PATH = rel_path("bridge_feishu_log")
LOCAL_V1_INFER_URL = local_service_url("oris_v1_infer_url")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path, record):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def feishu_profile():
    return ((((CFG.get("bridges") or {}).get("channel_profiles") or {}).get("feishu")) or {})

def choose_role(text: str) -> str:
    t = (text or "").strip().lower()
    routing = role_routing()
    profile = feishu_profile()

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

    return profile.get("default_general_role", "primary_general")

def apply_exact_reply_rule(input_text: str, raw_reply: str):
    text = (input_text or "").strip()
    reply = (raw_reply or "").strip()

    for p in exact_reply_patterns():
        m = re.match(p, text, flags=re.IGNORECASE)
        if m:
            forced = m.group(1).strip()
            forced = forced.strip('“”"\' ')
            return forced, "exact_reply_rule"

    return reply, "model_raw"

def apply_meta_question_rule(input_text: str):
    text = (input_text or "").strip()
    for rule in feishu_profile().get("meta_question_rules", []):
        pattern = rule.get("pattern")
        reply = (rule.get("reply") or "").strip()
        if pattern and reply and re.match(pattern, text, flags=re.IGNORECASE):
            return reply, "meta_question_rule"
    return None, None

def sanitize_reply(reply_text: str):
    text = (reply_text or "").strip()
    profile = feishu_profile()
    fallback = profile.get("unsafe_reply_fallback", "我是 Oris，会按问题类型自动选择合适模型与能力；你直接看结果就行。")
    markers = profile.get("unsafe_markers", [])

    lowered = text.lower()
    for marker in markers:
        if marker.lower() in lowered:
            return fallback, "unsafe_reply_guard"

    max_chars = int(profile.get("max_reply_chars", 1200))
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()

    return text, "sanitized_model_reply"

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
            "User-Agent": "ORIS-Feishu-Bridge/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sender-open-id", required=True)
    ap.add_argument("--chat-id", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--source", default=default_source("feishu_bridge"))
    ap.add_argument("--role", default=None)
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
        "sender_open_id": args.sender_open_id,
        "chat_id": args.chat_id,
        "input_text_preview": args.text[:300],
        "selected_role": role,
    }

    meta_reply, meta_policy = apply_meta_question_rule(args.text)
    if meta_reply:
        record["ok"] = True
        record["reply_policy"] = meta_policy
        record["oris_response"] = None
        record["reply_text_preview"] = meta_reply[:300]
        append_jsonl(LOG_PATH, record)

        print(json.dumps({
            "ok": True,
            "request_id": request_id,
            "bridge": {
                "channel": "feishu",
                "sender_open_id": args.sender_open_id,
                "chat_id": args.chat_id,
                "selected_role": role,
                "reply_policy": meta_policy,
            },
            "reply_text": meta_reply,
            "oris_result": None,
        }, ensure_ascii=False, indent=2))
        return

    try:
        result = call_oris(
            role=role,
            prompt=args.text,
            source=args.source,
            request_id=request_id,
            api_key=api_key,
        )

        raw_reply = (((result.get("data") or {}).get("text")) or "").strip()
        reply_text, reply_policy = apply_exact_reply_rule(args.text, raw_reply)

        if reply_policy != "exact_reply_rule":
            reply_text, sanitized_policy = sanitize_reply(reply_text)
            reply_policy = sanitized_policy

        record["ok"] = bool(result.get("ok"))
        record["reply_policy"] = reply_policy
        record["oris_response"] = result
        record["reply_text_preview"] = reply_text[:300]
        append_jsonl(LOG_PATH, record)

        print(json.dumps({
            "ok": bool(result.get("ok")),
            "request_id": request_id,
            "bridge": {
                "channel": "feishu",
                "sender_open_id": args.sender_open_id,
                "chat_id": args.chat_id,
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
                "channel": "feishu",
                "sender_open_id": args.sender_open_id,
                "chat_id": args.chat_id,
                "selected_role": role,
            },
            "error": f"{type(e).__name__}: {e}",
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)

if __name__ == "__main__":
    main()
