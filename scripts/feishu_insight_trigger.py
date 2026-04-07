#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_CFG = ROOT / "config" / "insight_skill_runtime.json"
INGRESS_LOG = ROOT / "orchestration" / "feishu_event_ingress_log.jsonl"
STATE_PATH = ROOT / "orchestration" / "generic_insight_trigger_state.json"
TRIGGER_LOG = ROOT / "orchestration" / "generic_insight_trigger_log.jsonl"
SEND = ROOT / "scripts" / "send_feishu_text_message.py"

DOWNLOADABLE_EXTS = {".docx", ".xlsx", ".pptx", ".pdf", ".zip"}

def resolve_pipeline():
    try:
        cfg = json.loads(RUNTIME_CFG.read_text(encoding="utf-8"))
        rel = (((cfg.get("generic_runtime") or {}).get("generic_pipeline_script")) or "scripts/run_generic_insight_pipeline_plus.py").strip()
        p = Path(rel)
        if not p.is_absolute():
            p = ROOT / p
        return p
    except Exception:
        return ROOT / "scripts" / "run_generic_insight_pipeline_plus.py"

PIPELINE = resolve_pipeline()

def ensure_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, obj: dict):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def load_state():
    if STATE_PATH.exists():
        try:
            state = load_json(STATE_PATH)
            if not isinstance(state.get("processed_keys"), list):
                state["processed_keys"] = []
            if "offset" not in state:
                state["offset"] = 0
            return state
        except Exception:
            pass
    return {"offset": 0, "processed_keys": []}

def save_state(state):
    save_json(STATE_PATH, state)

def append_log(obj):
    ensure_file(TRIGGER_LOG)
    with TRIGGER_LOG.open("a", encoding="utf-8") as f:
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

    message_id = (
        message.get("message_id")
        or payload.get("message_id")
        or payload.get("msg_id")
    )
    chat_id = (
        message.get("chat_id")
        or event.get("chat_id")
        or payload.get("chat_id")
    )
    event_type = (
        (payload.get("header") or {}).get("event_type")
        or payload.get("event_type")
        or payload.get("schema")
        or "unknown"
    )
    message_type = (
        message.get("message_type")
        or payload.get("message_type")
        or "unknown"
    )
    return {
        "message_id": message_id,
        "chat_id": chat_id,
        "event_type": event_type,
        "message_type": message_type,
    }

def make_trigger_key(line: str, meta: dict):
    mid = (meta.get("message_id") or "").strip()
    if mid:
        return f"message_id:{mid}", "message_id"
    return hashlib.sha256(line.encode("utf-8")).hexdigest(), "line_sha256"

def should_attempt(text: str):
    s = (text or "").strip()
    if len(s) < 20:
        return False

    lower = s.lower()
    report_intent = any(k in lower or k in s for k in [
        "报告", "洞察", "分析", "研究", "汇报", "简报",
        "ppt", "word", "excel", "deck", "briefing",
        "竞争对手", "商业合作", "合作方案", "行业", "客户场景", "技术栈"
    ])
    return report_intent

def parse_json_text(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        chunk = s[start:end+1]
        try:
            return json.loads(chunk)
        except Exception:
            return None
    return None

def extract_artifact_paths(result_obj: dict):
    payload = result_obj.get("payload") or {}
    items = (
        payload.get("report_build_artifacts")
        or payload.get("company_profile_artifacts")
        or payload.get("internal_report_build_artifacts")
        or payload.get("internal_company_profile_artifacts")
        or []
    )
    paths = []
    for x in items:
        if isinstance(x, dict):
            p = x.get("path")
            if isinstance(p, str) and p.strip():
                paths.append(p.strip())
    return paths

def count_downloadable_artifacts(paths):
    n = 0
    for p in paths:
        if Path(p).suffix.lower() in DOWNLOADABLE_EXTS:
            n += 1
    return n

def send_ack(chat_id: str):
    if not chat_id:
        return None

    ack_dir = ROOT / "orchestration" / "tmp"
    ack_dir.mkdir(parents=True, exist_ok=True)
    ack_file = ack_dir / f"ack_{int(time.time() * 1000)}.txt"
    ack_file.write_text(
        "已收到，正在生成洞察。\n当前版本按顺序执行；如果前面有任务，会在完成后自动回复结果。",
        encoding="utf-8"
    )

    r = subprocess.run(
        ["/usr/bin/python3", str(SEND), "--chat-id", chat_id, "--text-file", str(ack_file)],
        capture_output=True, text=True, check=False
    )
    return {
        "returncode": r.returncode,
        "stdout_tail": (r.stdout or "")[-2000:],
        "stderr_tail": (r.stderr or "")[-1000:]
    }

def build_pipeline_cmd(text: str, chat_id: str | None):
    cmd = [
        "/usr/bin/python3",
        str(PIPELINE),
        "--prompt-text",
        text,
        "--enable-register-delivery",
    ]
    if chat_id:
        cmd.extend(["--chat-id", chat_id])
    return cmd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-at-end", action="store_true")
    ap.add_argument("--poll-seconds", type=int, default=2)
    args = ap.parse_args()

    ensure_file(INGRESS_LOG)
    ensure_file(TRIGGER_LOG)

    state = load_state()
    if args.start_at_end and state.get("offset", 0) == 0 and INGRESS_LOG.exists():
        state["offset"] = INGRESS_LOG.stat().st_size
        save_state(state)

    print(json.dumps({
        "ok": True,
        "watching": str(INGRESS_LOG),
        "trigger_log": str(TRIGGER_LOG),
        "pipeline": str(PIPELINE),
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
                trigger_key, trigger_source = make_trigger_key(line, meta)

                if trigger_key in state.get("processed_keys", []):
                    continue

                text = extract_prompt_text(payload)

                if not should_attempt(text):
                    state.setdefault("processed_keys", []).append(trigger_key)
                    state["processed_keys"] = state["processed_keys"][-1000:]
                    save_state(state)
                    continue

                ack_info = send_ack(meta.get("chat_id"))

                r = subprocess.run(
                    build_pipeline_cmd(text, meta.get("chat_id")),
                    capture_output=True, text=True, check=False
                )

                result_obj = parse_json_text(r.stdout) if r.returncode == 0 else None
                payload_obj = (result_obj or {}).get("payload") or {}
                artifact_paths = extract_artifact_paths(result_obj or {})
                artifact_count = count_downloadable_artifacts(artifact_paths)

                chat_send_result = payload_obj.get("chat_send_result")
                if isinstance(chat_send_result, dict):
                    chat_send_ok = chat_send_result.get("ok")
                else:
                    chat_send_ok = None

                append_log({
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "trigger_key": trigger_key,
                    "trigger_source": trigger_source,
                    "message_id": meta.get("message_id"),
                    "chat_id": meta.get("chat_id"),
                    "event_type": meta.get("event_type"),
                    "message_type": meta.get("message_type"),
                    "pipeline": str(PIPELINE),
                    "ack_returncode": (ack_info or {}).get("returncode"),
                    "returncode": r.returncode,
                    "case_code": (result_obj or {}).get("case_code"),
                    "profile_code": (result_obj or {}).get("profile_code"),
                    "analysis_type": (result_obj or {}).get("analysis_type"),
                    "artifact_count": artifact_count,
                    "artifact_paths": artifact_paths,
                    "registered_count": payload_obj.get("registered_count"),
                    "delivery_executor_rc": payload_obj.get("delivery_executor_rc"),
                    "compiler_parser_mode": payload_obj.get("compiler_parser_mode"),
                    "compiler_execution_mode": payload_obj.get("compiler_execution_mode"),
                    "chat_delivery_mode": payload_obj.get("chat_delivery_mode"),
                    "chat_reply_path": payload_obj.get("chat_reply_path"),
                    "source_link_count": payload_obj.get("source_link_count"),
                    "chat_send_ok": chat_send_ok,
                    "prompt_preview": text[:500],
                    "stdout_tail": (r.stdout or "")[-6000:],
                    "stderr_tail": (r.stderr or "")[-2000:]
                })

                state.setdefault("processed_keys", []).append(trigger_key)
                state["processed_keys"] = state["processed_keys"][-1000:]
                save_state(state)

        save_state(state)
        time.sleep(args.poll_seconds)

if __name__ == "__main__":
    main()
