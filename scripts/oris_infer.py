#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from oris_vnext.infer_refresh import InferRefresh
from oris_vnext.openai_chat_contract import legacy_prompt_request, load_chat_request


ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = ROOT / "scripts" / "runtime_execute.py"
LOG_PATH = ROOT / "orchestration" / "execution_log.jsonl"


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


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _append(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _parse_output(value: str) -> dict:
    decoded = json.loads((value or "").strip())
    if not isinstance(decoded, dict):
        raise RuntimeError("executor output must be an object")
    return decoded


def main() -> int:
    args = _parser().parse_args()
    request_id = args.request_id or str(uuid.uuid4())
    request = (
        load_chat_request(Path(args.request_file))
        if args.request_file
        else legacy_prompt_request(str(args.prompt))
    )
    refresh = InferRefresh(ROOT)
    preflight = refresh.preflight(args.role)
    command = [
        "/usr/bin/python3",
        str(EXECUTOR),
        "--role",
        args.role,
    ]
    if args.request_file:
        command.extend(["--request-file", args.request_file])
    else:
        command.extend(["--prompt", str(args.prompt)])
    if args.show_raw:
        command.append("--show-raw")
    result = _run(command)
    record = {
        "request_id": request_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "role": args.role,
        "request_metadata": request.metadata(),
        "executor_returncode": result.returncode,
        "preflight_warnings": preflight,
        "conversation_content_recorded": False,
        "tool_schema_recorded": False,
        "tool_arguments_or_results_recorded": False,
    }
    parsed: dict | None = None
    try:
        parsed = _parse_output(result.stdout)
        record.update(
            {
                "ok": bool(parsed.get("ok")),
                "selected_model": parsed.get("selected_model"),
                "execution_primary": parsed.get("execution_primary"),
                "used_provider": parsed.get("used_provider"),
                "used_model": parsed.get("used_model"),
                "attempt": parsed.get("attempt"),
                "tool_call_count": int(parsed.get("tool_call_count") or 0),
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
    postflight = refresh.postflight()
    record["post_refresh_warnings"] = postflight
    _append(record)
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
            "preflight_warnings": preflight,
            "post_refresh_warnings": postflight,
        }
    )
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return 0 if parsed.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
