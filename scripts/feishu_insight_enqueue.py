#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGRESS_LOG = ROOT / "orchestration" / "feishu_event_ingress_log.jsonl"
QUEUE_LOG = ROOT / "orchestration" / "generic_insight_queue.jsonl"
STATE_PATH = ROOT / "orchestration" / "generic_insight_enqueue_state.json"
ENQUEUE_LOG = ROOT / "orchestration" / "generic_insight_enqueue_log.jsonl"
LOCK_PATH = ROOT / "orchestration" / "generic_insight_enqueue.lock"

def ensure_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def append_jsonl(path: Path, obj):
    ensure_file(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def extract_strings(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            extract_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            extract_strings(v, out)
    elif isinstance(obj, str):
        s = obj.strip()
        if s:
            out.append(s)

def extract_prompt_text(payload: dict):
    candidates = [
        (((payload.get("event") or {}).get("message") or {}).get("content")),
        (((payload.get("event") or {}).get("text"))),
        payload.get("content"),
        payload.get("text"),
        payload.get("text_preview"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()

    parts = []
    extract_strings(payload, parts)
    return "\n".join(parts).strip()

def extract_message_meta(payload: dict):
    event = payload.get("event") or {}
    message = event.get("message") or {}
    return {
        "message_id": message.get("message_id") or payload.get("message_id") or payload.get("msg_id"),
        "chat_id": message.get("chat_id") or event.get("chat_id") or payload.get("chat_id"),
        "event_type": ((payload.get("header") or {}).get("event_type") or payload.get("event_type") or "unknown"),
        "message_type": (message.get("message_type") or payload.get("message_type") or "unknown"),
    }

def make_job_key(line: str, meta: dict):
    mid = (meta.get("message_id") or "").strip()
    if mid:
        return f"message_id:{mid}"
    return hashlib.sha256(line.encode("utf-8")).hexdigest()

def should_attempt(text: str):
    s = (text or "").strip()
    if len(s) < 20:
        return False
    lower = s.lower()
    keywords = [
        "报告", "洞察", "分析", "研究", "评估", "方案", "简报", "研判",
        "公司", "企业", "客户", "伙伴", "竞争", "行业", "商务", "解决方案", "合作",
        "report", "insight", "analysis", "company", "customer", "partner", "industry", "solution"
    ]
    return any(k in s or k in lower for k in keywords)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-at-end", action="store_true")
    ap.add_argument("--poll-seconds", type=int, default=2)
    args = ap.parse_args()

    ensure_file(INGRESS_LOG)
    ensure_file(QUEUE_LOG)
    ensure_file(ENQUEUE_LOG)
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    lockf = LOCK_PATH.open("w")
    try:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("enqueue already running")

    state = load_json(STATE_PATH, {"offset": 0, "processed_keys": []})
    if args.start_at_end and state.get("offset", 0) == 0 and INGRESS_LOG.exists():
        state["offset"] = INGRESS_LOG.stat().st_size
        save_json(STATE_PATH, state)

    print(json.dumps({
        "ok": True,
        "mode": "enqueue",
        "watching": str(INGRESS_LOG),
        "queue": str(QUEUE_LOG),
        "state": state
    }, ensure_ascii=False))

    while True:
        with INGRESS_LOG.open("r", encoding="utf-8") as f:
            f.seek(state.get("offset", 0))
            while True:
                line = f.readline()
                if not line:
                    break
                state["offset"] = f.tell()

                try:
                    payload = json.loads(line)
                except Exception:
                    payload = {"raw_line": line.strip()}

                meta = extract_message_meta(payload)
                text = extract_prompt_text(payload)
                job_key = make_job_key(line, meta)

                if job_key in state.get("processed_keys", []):
                    continue

                if should_attempt(text):
                    job = {
                        "job_key": job_key,
                        "message_id": meta.get("message_id"),
                        "chat_id": meta.get("chat_id"),
                        "event_type": meta.get("event_type"),
                        "message_type": meta.get("message_type"),
                        "prompt_text": text,
                        "enqueue_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                    append_jsonl(QUEUE_LOG, job)
                    append_jsonl(ENQUEUE_LOG, {"action": "queued", **job})

                state.setdefault("processed_keys", []).append(job_key)
                state["processed_keys"] = state["processed_keys"][-2000:]
                save_json(STATE_PATH, state)

        save_json(STATE_PATH, state)
        time.sleep(args.poll_seconds)

if __name__ == "__main__":
    main()
