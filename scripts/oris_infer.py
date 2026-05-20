#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUOTA_PROBE_SCRIPT = ROOT / "scripts" / "quota_probe.py"
PROVIDER_SCOREBOARD_SCRIPT = ROOT / "scripts" / "provider_scoreboard.py"
MODEL_SELECTOR_SCRIPT = ROOT / "scripts" / "model_selector.py"
RUNTIME_PLAN_SCRIPT = ROOT / "scripts" / "runtime_plan.py"
RUNTIME_EXECUTE_SCRIPT = ROOT / "scripts" / "runtime_execute.py"
LOG_PATH = ROOT / "orchestration" / "execution_log.jsonl"
RUNTIME_PLAN_PATH = ROOT / "orchestration" / "runtime_plan.json"
ACTIVE_ROUTING_PATH = ROOT / "orchestration" / "active_routing.json"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def utc_dt():
    return datetime.now(timezone.utc)


def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def parse_json_output(text: str):
    text = (text or "").strip()
    if not text:
        raise RuntimeError("empty output")
    return json.loads(text)


def load_json_or_none(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


def parse_ts(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def artifact_is_fresh(path: Path, ttl_seconds: int) -> bool:
    raw = load_json_or_none(path)
    if not raw:
        return False
    generated_at = parse_ts(raw.get("generated_at") or raw.get("updated_at"))
    if not generated_at:
        return False
    age = (utc_dt() - generated_at.astimezone(timezone.utc)).total_seconds()
    return age >= 0 and age <= ttl_seconds


def refresh_ttl_seconds() -> int:
    value = os.getenv("ORIS_INFER_REFRESH_TTL_SECONDS", "600")
    try:
        return max(0, int(value))
    except Exception:
        return 600


def refresh_forced() -> bool:
    return os.getenv("ORIS_INFER_FORCE_REFRESH", "").lower() in {"1", "true", "yes"}


def append_jsonl(path: Path, record: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_refresh(script_path: Path, required: bool = True):
    result = run_cmd(["/usr/bin/python3", str(script_path)])
    if result.returncode != 0 and required:
        raise SystemExit(f"{script_path.name} refresh failed:\n{result.stderr or result.stdout}")
    return result


def preflight_refresh():
    warnings = []
    ttl = refresh_ttl_seconds()
    active_fresh = artifact_is_fresh(ACTIVE_ROUTING_PATH, ttl)
    plan_fresh = artifact_is_fresh(RUNTIME_PLAN_PATH, ttl)

    if not refresh_forced() and active_fresh and plan_fresh:
        warnings.append({
            "stage": "preflight",
            "script": "refresh_skipped",
            "reason": "runtime_artifacts_fresh",
            "ttl_seconds": ttl,
        })
        return warnings

    for script_path in [QUOTA_PROBE_SCRIPT, PROVIDER_SCOREBOARD_SCRIPT]:
        result = run_refresh(script_path, required=False)
        if result.returncode != 0:
            warnings.append({
                "script": script_path.name,
                "stage": "preflight",
                "stderr": (result.stderr or result.stdout or "").strip()[:500],
            })

    run_refresh(MODEL_SELECTOR_SCRIPT, required=True)
    run_refresh(RUNTIME_PLAN_SCRIPT, required=True)
    return warnings


def postflight_refresh():
    warnings = []
    if os.getenv("ORIS_INFER_POST_REFRESH", "").lower() not in {"1", "true", "yes"}:
        warnings.append({
            "stage": "postflight",
            "script": "refresh_skipped",
            "reason": "post_refresh_disabled_by_default",
        })
        return warnings

    for script_path in [
        QUOTA_PROBE_SCRIPT,
        PROVIDER_SCOREBOARD_SCRIPT,
        MODEL_SELECTOR_SCRIPT,
        RUNTIME_PLAN_SCRIPT,
    ]:
        result = run_refresh(script_path, required=False)
        if result.returncode != 0:
            warnings.append({
                "script": script_path.name,
                "stage": "postflight",
                "stderr": (result.stderr or result.stdout or "").strip()[:500],
            })
    return warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--request-id", default=None)
    ap.add_argument("--source", default="manual_cli")
    ap.add_argument("--show-raw", action="store_true")
    args = ap.parse_args()

    request_id = args.request_id or str(uuid.uuid4())

    preflight_warnings = preflight_refresh()

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
        "preflight_warnings": preflight_warnings,
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

    post_refresh_warnings = postflight_refresh()
    record["post_refresh_warnings"] = post_refresh_warnings

    append_jsonl(LOG_PATH, record)

    if parsed is not None:
        parsed["request_id"] = request_id
        parsed["source"] = args.source
        parsed["preflight_warnings"] = preflight_warnings
        parsed["post_refresh_warnings"] = post_refresh_warnings
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        raise SystemExit(0 if parsed.get("ok") else 2)

    print(json.dumps({
        "ok": False,
        "request_id": request_id,
        "error": "executor_output_not_json",
        "preflight_warnings": preflight_warnings,
        "post_refresh_warnings": post_refresh_warnings,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
