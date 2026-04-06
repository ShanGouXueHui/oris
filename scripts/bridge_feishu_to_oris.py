#!/usr/bin/env python3
import argparse
import json
import os
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
LOG_PATH = ROOT / "orchestration" / "bridge_feishu_log.jsonl"
LOCAL_V1_INFER_URL = "http://127.0.0.1:8788/v1/infer"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def append_jsonl(path: Path, record: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_api_key():
    if not SECRETS_PATH.exists():
        return None
    data = load_json(SECRETS_PATH)
    return (((data.get("services") or {}).get("oris_api") or {}).get("bearerToken"))

def choose_role(text: str) -> str:
    t = (text or "").strip().lower()

    coding_keywords = [
        "代码", "报错", "debug", "bug", "python", "javascript", "typescript",
        "fastapi", "接口", "api", "脚本", "deploy", "nginx", "systemd", "sql"
    ]
    report_keywords = [
        "报告", "洞察", "分析", "研报", "复盘", "总结", "report", "insight"
    ]
    cn_keywords = [
        "国产", "中文模型", "阿里", "腾讯", "智谱", "混元", "百炼", "qwen", "glm"
    ]
    cheap_keywords = [
        "省钱", "便宜", "低成本", "免费", "fallback", "控成本"
    ]

    if any(k in t for k in coding_keywords):
        return "coding"
    if any(k in t for k in report_keywords):
        return "report_generation"
    if any(k in t for k in cn_keywords):
        return "cn_candidate_pool"
    if any(k in t for k in cheap_keywords):
        return "free_fallback"
    return "primary_general"

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
    ap.add_argument("--role", default=None)
    ap.add_argument("--source", default="feishu_bridge_core")
    args = ap.parse_args()

    api_key = read_api_key()
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

    try:
        result = call_oris(role=role, prompt=args.text, source=args.source, request_id=request_id, api_key=api_key)
        reply_text = (((result.get("data") or {}).get("text")) or "").strip()

        record["ok"] = bool(result.get("ok"))
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
