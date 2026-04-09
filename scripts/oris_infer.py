#!/usr/bin/env python3
import argparse
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_SELECTOR_SCRIPT = ROOT / "scripts" / "model_selector.py"
RUNTIME_PLAN_SCRIPT = ROOT / "scripts" / "runtime_plan.py"
RUNTIME_EXECUTE_SCRIPT = ROOT / "scripts" / "runtime_execute.py"
LOG_PATH = ROOT / "orchestration" / "execution_log.jsonl"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def parse_json_output(text: str):
    text = (text or "").strip()
    if not text:
        raise RuntimeError("empty output")
    return json.loads(text)

def append_jsonl(path: Path, record: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--request-id", default=None)
    ap.add_argument("--source", default="manual_cli")
    ap.add_argument("--show-raw", action="store_true")
    args = ap.parse_args()

    request_id = args.request_id or str(uuid.uuid4())

    refresh = run_cmd(["/usr/bin/python3", str(RUNTIME_PLAN_SCRIPT)])
    if refresh.returncode != 0:
        raise SystemExit(f"runtime_plan refresh failed:\n{refresh.stderr}")

    exec_cmd = [
        "/usr/bin/python3",
        str(RUNTIME_EXECUTE_SCRIPT),
        "--role", args.role,
        "--prompt", args.prompt,
    ]
    if args.show_raw:
        exec_cmd.append("--show-raw")

    result = run_cmd(exec_cmd)

    record = {
        "request_id": request_id,
        "ts": utc_now(),
        "source": args.source,
        "role": args.role,
        "prompt_preview": args.prompt[:200],
        "prompt_length": len(args.prompt),
        "executor_returncode": result.returncode,
    }

    parsed = None
    try:
        parsed = parse_json_output(result.stdout)
        record["ok"] = parsed.get("ok", False)
        record["selected_model"] = parsed.get("selected_model")
        record["execution_primary"] = parsed.get("execution_primary")
        record["used_provider"] = parsed.get("used_provider")
        record["used_model"] = parsed.get("used_model")
        record["attempt"] = parsed.get("attempt")
        record["text_preview"] = (parsed.get("text") or "")[:300]
        record["attempts_log"] = parsed.get("attempts_log", [])
    except Exception as e:
        record["ok"] = False
        record["parse_error"] = f"{type(e).__name__}: {e}"
        record["stdout_preview"] = (result.stdout or "")[:500]
        record["stderr_preview"] = (result.stderr or "")[:500]

    append_jsonl(LOG_PATH, record)

    post_refresh = run_cmd(["/usr/bin/python3", str(RUNTIME_PLAN_SCRIPT)])
    if post_refresh.returncode != 0:
        print(json.dumps({
            "ok": False,
            "request_id": request_id,
            "error": "post_runtime_plan_refresh_failed",
            "stderr": post_refresh.stderr,
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)

    if parsed is not None:
        parsed["request_id"] = request_id
        parsed["source"] = args.source
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        raise SystemExit(0 if parsed.get("ok") else 2)

    print(json.dumps({
        "ok": False,
        "request_id": request_id,
        "error": "executor_output_not_json",
    }, ensure_ascii=False, indent=2))
    raise SystemExit(2)

if __name__ == "__main__":
    main()
