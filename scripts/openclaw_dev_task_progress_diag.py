#!/usr/bin/env python3
"""Capture OpenClaw dev-task progress signals.

This diagnostic distinguishes UI still-waiting from backend activity by reading:
- openclaw gateway logs
- ORIS Free Mesh latency events
- git status / recent commits
- recent dev_employee artifacts
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_dev_task_progress.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_dev_task_progress.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: str, timeout: int = 20) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": (p.stdout or "")[-12000:], "stderr": (p.stderr or "")[-4000:], "timeout": False}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "stdout": str(exc.stdout or "")[-12000:], "stderr": str(exc.stderr or "")[-4000:], "timeout": True}


def classify(gateway_logs: str, git_status: str, latest_artifacts: str) -> dict[str, Any]:
    lower = gateway_logs.lower()
    signals = {
        "webchat_connected": "webchat connected" in lower,
        "webchat_disconnected": "webchat disconnected" in lower,
        "agent_failed": "agent failed" in lower or "failed before reply" in lower,
        "tool_activity": any(x in lower for x in ["tool", "commands.", "sessions.", "models.", "chat.history"]),
        "openclaw_error": any(x in lower for x in ["error", "exception", "failed", "timeout"]),
        "repo_changed": bool(git_status.strip()),
        "dev_artifacts_seen": bool(latest_artifacts.strip()),
    }
    if signals["agent_failed"] or signals["openclaw_error"]:
        state = "error_or_blocked"
    elif signals["repo_changed"] or signals["dev_artifacts_seen"]:
        state = "working_or_completed"
    elif signals["webchat_connected"] and signals["tool_activity"]:
        state = "connected_waiting_no_repo_effect_yet"
    else:
        state = "unknown"
    return {"state": state, "signals": signals}


def main() -> int:
    gateway = run("journalctl --user -u openclaw-gateway.service -n 260 --no-pager", timeout=20)
    mesh = run("tail -n 40 logs/dev_employee/free_mesh_latency_events.jsonl 2>/dev/null || true", timeout=10)
    git_status = run("git status --short", timeout=10)
    git_log = run("git log --oneline -n 8", timeout=10)
    artifacts = run("find logs/dev_employee -maxdepth 2 -type f -printf '%TY-%Tm-%Td %TH:%TM %p\\n' 2>/dev/null | sort | tail -n 40", timeout=10)
    procs = run("ps -eo pid,etimes,cmd | grep -E 'openclaw|oris_free_mesh|oris_infer|git ' | grep -v grep | tail -n 80", timeout=10)

    logs_text = (gateway.get("stdout") or "") + "\n" + (gateway.get("stderr") or "")
    classification = classify(logs_text, git_status.get("stdout", ""), artifacts.get("stdout", ""))

    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "classification": classification,
        "gateway_logs_tail": gateway,
        "free_mesh_latency_tail": mesh,
        "git_status": git_status,
        "git_log": git_log,
        "recent_dev_employee_artifacts": artifacts,
        "processes": procs,
        "interpretation": {
            "ui_in_progress_is_not_enough": True,
            "recommended_operator_view": "Use this artifact or journalctl --user -u openclaw-gateway.service -f to distinguish active work from a hang.",
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Dev Task Progress Diagnostic\n\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- state: `{classification['state']}`\n"
        f"- webchat_connected: `{classification['signals']['webchat_connected']}`\n"
        f"- agent_failed: `{classification['signals']['agent_failed']}`\n"
        f"- openclaw_error: `{classification['signals']['openclaw_error']}`\n"
        f"- repo_changed: `{classification['signals']['repo_changed']}`\n"
        f"- dev_artifacts_seen: `{classification['signals']['dev_artifacts_seen']}`\n\n"
        "## Operator Note\n\n"
        "The OpenClaw UI `In progress` indicator alone cannot prove whether the agent is actively working or hung. Use gateway logs, repo changes, and dev_employee artifacts as progress evidence.\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "state": classification["state"], "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
