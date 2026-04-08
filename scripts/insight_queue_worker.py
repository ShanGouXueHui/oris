#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE_LOG = ROOT / "orchestration" / "generic_insight_queue.jsonl"
STATE_PATH = ROOT / "orchestration" / "generic_insight_worker_state.json"
WORKER_LOG = ROOT / "orchestration" / "generic_insight_worker_log.jsonl"
LOCK_PATH = ROOT / "orchestration" / "generic_insight_worker.lock"
DELIVERY_CFG_PATH = ROOT / "config" / "insight_delivery_config.json"

PIPELINE = ROOT / "scripts" / "run_generic_insight_pipeline_plus.py"
SENDER = ROOT / "scripts" / "send_feishu_text_message.py"

DEFAULT_DELIVERY_CFG = {
    "feishu_chunk_limit": 1800,
    "ack_text": "已收到你的洞察请求，正在分析中。\n默认优先返回适合手机直接阅读的结构化结论；若你明确要求 Word / PPT / Excel，再走正式材料模式。",
    "render_fail_text": "本次洞察未形成可审计的聊天正文；我已阻断占位内容发送，并记录问题。",
    "exec_fail_text": "这条洞察任务执行失败了，我已记录错误并保留原始请求。请稍后重试。",
    "entity_block_text": "当前未能稳定识别本次要分析的目标公司，已阻断正式洞察生成。请直接给出明确公司名称，或减少行业词/竞品混杂表述后再试。",
    "placeholder_blocklist": [],
    "send_rules": {
        "allow_direct_send_inside_pipeline": False,
        "worker_is_single_sender": True
    }
}


def ensure_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_delivery_cfg():
    cfg = load_json(DELIVERY_CFG_PATH, {})
    if not isinstance(cfg, dict):
        cfg = {}
    merged = json.loads(json.dumps(DEFAULT_DELIVERY_CFG, ensure_ascii=False))
    merged.update({k: v for k, v in cfg.items() if k != "send_rules"})
    merged["send_rules"] = {**DEFAULT_DELIVERY_CFG.get("send_rules", {}), **(cfg.get("send_rules") or {})}
    if not isinstance(merged.get("placeholder_blocklist"), list):
        merged["placeholder_blocklist"] = []
    return merged


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj):
    ensure_file(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


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
        try:
            return json.loads(s[start:end + 1])
        except Exception:
            return None
    return None


def send_text(chat_id: str, text: str):
    if not chat_id or not text:
        return None
    r = subprocess.run(
        ["python3", str(SENDER), "--chat-id", chat_id, "--text", text],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    return {
        "returncode": r.returncode,
        "stdout_tail": (r.stdout or "")[-4000:],
        "stderr_tail": (r.stderr or "")[-2000:],
    }


def run_pipeline(job: dict):
    cmd = [
        "python3", str(PIPELINE),
        "--prompt-text", job["prompt_text"],
        "--enable-register-delivery"
    ]
    if job.get("chat_id"):
        cmd += ["--chat-id", job["chat_id"]]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(ROOT))
    obj = parse_json_text(r.stdout) if r.returncode == 0 else None
    return r, obj


def read_text_file(path_str: str):
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def split_for_feishu(text: str, limit: int = 1800):
    text = (text or "").strip()
    if not text:
        return []

    chunks = []
    buf = ""

    for line in text.splitlines(True):
        if len(buf) + len(line) <= limit:
            buf += line
            continue

        if buf.strip():
            chunks.append(buf.strip())
            buf = ""

        while len(line) > limit:
            part = line[:limit]
            if part.strip():
                chunks.append(part.strip())
            line = line[limit:]

        buf += line

    if buf.strip():
        chunks.append(buf.strip())

    return chunks


def looks_like_placeholder(text: str, cfg: dict):
    t = (text or "").strip()
    if not t:
        return True

    bad_signals = cfg.get("placeholder_blocklist") or []
    for s in bad_signals:
        if s in t:
            return True

    if t.startswith("# 请基于最新可得信息，对"):
        return True
    if t.startswith("# 请仅识别一个明确公司主体进行洞察"):
        return True

    return False


def render_chat_markdown(payload: dict, delivery_cfg: dict):
    chat_reply_path = payload.get("chat_reply_path")
    raw_md = read_text_file(chat_reply_path)

    render_info = {
        "ok": False,
        "blocked": False,
        "entity": None,
        "snapshot_count": None,
        "evidence_count": None,
        "metric_count": None,
        "markdown": raw_md[:4000] if raw_md else "",
        "renderer_rc": 0,
        "renderer_stdout_tail": "",
        "renderer_stderr_tail": "",
    }

    official = payload.get("official_ingest_summary") or {}
    core_data = official.get("core_data") or []
    core_map = {}
    for item in core_data:
        if isinstance(item, dict) and item.get("field"):
            core_map[item["field"]] = item.get("value")

    render_info["entity"] = core_map.get("entity")
    render_info["snapshot_count"] = core_map.get("written_snapshot_count")
    render_info["evidence_count"] = core_map.get("written_evidence_count")
    render_info["metric_count"] = core_map.get("written_metric_count")

    blocked = False
    if looks_like_placeholder(raw_md, delivery_cfg):
        blocked = True
    if not core_map.get("entity"):
        blocked = True
    if not core_map.get("written_snapshot_count"):
        blocked = True
    if not core_map.get("written_evidence_count"):
        blocked = True

    if blocked:
        render_info["blocked"] = True
        detail_lines = delivery_cfg.get("blocked_result_detail_lines") or []
        render_info["markdown"] = (
            "# 公司洞察\n\n"
            "## 执行摘要\n"
            f"- {delivery_cfg.get('blocked_result_summary_text')}\n\n"
            "## 风险与待验证\n"
            + "\n".join([f"- {x}" for x in detail_lines])
        )
        return render_info

    render_info["ok"] = True
    return render_info


def send_final_markdown(chat_id: str, markdown: str, delivery_cfg: dict):
    chunks = split_for_feishu(markdown, limit=int(delivery_cfg.get("feishu_chunk_limit", 1800)))
    results = []
    ok = True
    for chunk in chunks:
        one = send_text(chat_id, chunk)
        results.append(one)
        if not one or one.get("returncode") != 0:
            ok = False
            break
    return {
        "ok": ok,
        "chunk_count": len(chunks),
        "results": results,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poll-seconds", type=int, default=2)
    args = ap.parse_args()

    ensure_file(QUEUE_LOG)
    ensure_file(WORKER_LOG)
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    lockf = LOCK_PATH.open("w")
    try:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("worker already running")

    state = load_json(STATE_PATH, {"offset": 0})
    delivery_cfg = load_delivery_cfg()
    print(json.dumps({
        "ok": True,
        "mode": "worker",
        "queue": str(QUEUE_LOG),
        "state": state
    }, ensure_ascii=False))

    while True:
        with QUEUE_LOG.open("r", encoding="utf-8") as f:
            f.seek(state.get("offset", 0))
            while True:
                line = f.readline()
                if not line:
                    break

                try:
                    job = json.loads(line)
                except Exception:
                    state["offset"] = f.tell()
                    save_json(STATE_PATH, state)
                    continue

                ack = send_text(job.get("chat_id"), delivery_cfg.get("ack_text"))

                started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                r, obj = run_pipeline(job)
                finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                fail_notice = None
                render_info = None
                final_send = None
                precheck = None

                if r.returncode != 0:
                    fail_notice = send_text(job.get("chat_id"), delivery_cfg.get("exec_fail_text"))
                else:
                    payload = (obj or {}).get("payload") or {}
                    payload_precheck = payload.get("precheck") or (obj or {}).get("precheck") or {}

                    if isinstance(payload_precheck, dict) and payload_precheck.get("blocked"):
                        precheck = payload_precheck
                        fail_notice = send_text(job.get("chat_id"), delivery_cfg.get("entity_block_text"))
                    else:
                        render_info = render_chat_markdown(payload, delivery_cfg)

                        precheck = {
                            "entity": render_info.get("entity"),
                            "snapshot_count": render_info.get("snapshot_count"),
                            "evidence_count": render_info.get("evidence_count"),
                            "metric_count": render_info.get("metric_count"),
                            "blocked": render_info.get("blocked"),
                        }

                        if render_info.get("ok"):
                            final_send = send_final_markdown(job.get("chat_id"), render_info.get("markdown") or "", delivery_cfg)
                            if not final_send.get("ok"):
                                fail_notice = send_text(job.get("chat_id"), delivery_cfg.get("send_fail_text"))
                        else:
                            fail_notice = send_text(job.get("chat_id"), delivery_cfg.get("render_fail_text"))

                payload = (obj or {}).get("payload") or {}
                append_jsonl(WORKER_LOG, {
                    "job_key": job.get("job_key"),
                    "message_id": job.get("message_id"),
                    "chat_id": job.get("chat_id"),
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "returncode": r.returncode,
                    "case_code": (obj or {}).get("case_code"),
                    "profile_code": (obj or {}).get("profile_code"),
                    "analysis_type": (obj or {}).get("analysis_type"),
                    "chat_delivery_mode": payload.get("chat_delivery_mode"),
                    "chat_reply_path": payload.get("chat_reply_path"),
                    "registered_count": payload.get("registered_count"),
                    "delivery_executor_rc": payload.get("delivery_executor_rc"),
                    "ack": ack,
                    "fail_notice": fail_notice,
                    "precheck": precheck,
                    "render_info": render_info,
                    "final_send": final_send,
                    "stdout_tail": (r.stdout or "")[-12000:],
                    "stderr_tail": (r.stderr or "")[-4000:]
                })

                state["offset"] = f.tell()
                save_json(STATE_PATH, state)

        save_json(STATE_PATH, state)
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
