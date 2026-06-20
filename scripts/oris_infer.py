#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from oris_vnext.openai_chat_contract import legacy_prompt_request, load_chat_request


ROOT = Path(__file__).resolve().parents[1]
QUOTA_PROBE_SCRIPT = ROOT / "scripts" / "quota_probe.py"
PROVIDER_SCOREBOARD_SCRIPT = ROOT / "scripts" / "provider_scoreboard.py"
MODEL_SELECTOR_SCRIPT = ROOT / "scripts" / "model_selector.py"
RUNTIME_PLAN_SCRIPT = ROOT / "scripts" / "runtime_plan.py"
RUNTIME_EXECUTE_SCRIPT = ROOT / "scripts" / "runtime_execute.py"
LOG_PATH = ROOT / "orchestration" / "execution_log.jsonl"
RUNTIME_PLAN_PATH = ROOT / "orchestration" / "runtime_plan.json"
ACTIVE_ROUTING_PATH = ROOT / "orchestration" / "active_routing.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_dt() -> datetime:
    return datetime.now(timezone.utc)


def run_cmd(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def parse_json_output(text: str) -> dict:
    value = json.loads((text or "").strip())
    if not isinstance(value, dict):
        raise RuntimeError("executor output must be an object")
    return value


def load_json_or_none(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def artifact_is_fresh(path: Path, ttl_seconds: int) -> bool:
    raw = load_json_or_none(path)
    generated_at = parse_ts(
        (raw or {}).get("generated_at") or (raw or {}).get("updated_at")
    )
    if generated_at is None:
        return False
    age = (utc_dt() - generated_at.astimezone(timezone.utc)).total_seconds()
    return 0 <= age <= ttl_seconds


def refresh_ttl_seconds() -> int:
    try:
        return max(0, int(os.getenv("ORIS_INFER_REFRESH_TTL_SECONDS", "600")))
    except Exception:
        return 600


def refresh_forced() -> bool:
    return os.getenv("ORIS_INFER_FORCE_REFRESH", "").lower() in {
        "1",
        "true",
        "yes",
    }


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_refresh(
    script_path: Path,
    *,
    required: bool,
) -> subprocess.CompletedProcess[str]:
    result = run_cmd(["/usr/bin/python3", str(script_path)])
    if result.returncode != 0 and required:
        raise RuntimeError(f"{script_path.name} refresh failed")
    return result


def preflight_refresh() -> list[dict]:
    warnings: list[dict] = []
    ttl = refresh_ttl_seconds()
    if (
        not refresh_forced()
        and artifact_is_fresh(ACTIVE_ROUTING_PATH, ttl)
        and artifact_is_fresh(RUNTIME_PLAN_PATH, ttl)
    ):
        return [
            {
                "stage": "preflight",
                "script": "refresh_skipped",
                "reason": "runtime_artifacts_fresh",
                "ttl_seconds": ttl,
            }
        ]
    for script_path in (QUOTA_PROBE_SCRIPT, PROVIDER_SCOREBOARD_SCRIPT):
        result = run_refresh(script_path, required=False)
        if result.returncode != 0:
            warnings.append(
                {
                    "stage": "preflight",
                    "script": script_path.name,
                    "returncode": result.returncode,
                }
            )
    run_refresh(MODEL_SELECTOR_SCRIPT, required=True)
    run_refresh(RUNTIME_PLAN_SCRIPT, required=True)
    return warnings


def postflight_refresh() -> list[dict]:
    if os.getenv("ORIS_INFER_POST_REFRESH", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        return [
            {
                "stage": "postflight",
                "script": "refresh_skipped",
                "reason": "post_refresh_disabled_by_default",
            }
        ]
    warnings: list[dict] = []
    for script_path in (
        QUOTA_PROBE_SCRIPT,
        PROVIDER_SCOREBOARD_SCRIPT,
        MODEL_SELECTOR_SCRIPT,
        RUNTIME_PLAN_SCRIPT,
    ):
        result = run_refresh(script_path, required=False)
        if result.returncode != 0:
            warnings.append(
                {
                    "stage": "postflight",
                    "script": script_path.name,
                    "returncode": result.returncode,
                }
            )
    return warnings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt")
    source.add_argument("--request-file")
    parser.add_argument("--request-id", default=None)
    parser.add_argument("--source", default="manual_cli")
    parser.add_argument("--show-raw", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    request_id = args.request_id or str(uuid.uuid4())
    request = (
        load_chat_request(Path(args.request_file))
        if args.request_file
        else legacy_prompt_request(str(args.prompt))
    )
    preflight_warnings = preflight_refresh()
    command = [
        "/usr/bin/python3",
        str(RUNTIME_EXECUTE_SCRIPT),
        "--role",
        args.role,
    ]
    if args.request_file:
        command.extend(["--request-file", args.request_file])
    else:
        command.extend(["--prompt", str(args.prompt)])
    if args.show_raw:
        command.append("--show-raw")
    result = run_cmd(command)
    record = {
        "request_id": request_id,
        "ts": utc_now(),
        "source": args.source,
        "role": args.role,
        "request_metadata": request.metadata(),
        "executor_returncode": result.returncode,
        "preflight_warnings": preflight_warnings,
        "conversation_content_recorded": False,
        "tool_schema_recorded": False,
        "tool_arguments_or_results_recorded": False,
    }
    parsed: dict | None = None
    try:
        parsed = parse_json_output(result.stdout)
        record.update(
            {
                "ok": bool(parsed.get("ok")),
                "selected_model": parsed.get("selected_model"),
                "execution_primary": parsed.get("execution_primary"),
                "used_provider": parsed.get("used_provider"),
                "used_model": parsed.get("used_model"),
                "attempt": parsed.get("attempt"),
                "tool_call_count": parsed.get("tool_call_count", 0),
                "finish_reason": parsed.get("finish_reason"),
                "attempts_log": parsed.get("attempts_log", []),
            }
        )
    except Exception as exc:
        record.update(
            {
                "ok": False,
                "parse_error_type": type(exc).__name__,
                "stdout_bytes": len((result.stdout or "").encode("utf-8")),
                "stderr_bytes": len((result.stderr or "").encode("utf-8")),
            }
        )
    record["post_refresh_warnings"] = postflight_refresh()
    append_jsonl(LOG_PATH, record)
    if parsed is None:
        parsed = {
            "ok": False,
            "request_id": request_id,
            "error": "executor_output_not_json",
        }
    parsed.update(
        {
            "request_id": request_id,
            "source": args.source,
            "preflight_warnings": preflight_warnings,
            "post_refresh_warnings": record["post_refresh_warnings"],
        }
    )
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return 0 if parsed.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
