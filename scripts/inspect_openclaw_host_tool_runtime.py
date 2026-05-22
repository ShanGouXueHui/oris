#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_host_tool_runtime.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_host_tool_runtime.md"
MARKER = ROOT / "logs" / "dev_employee" / "host_runtime_marker.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: str, timeout: int = 25) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {
            "cmd": cmd,
            "rc": p.returncode,
            "stdout": (p.stdout or "")[-16000:],
            "stderr": (p.stderr or "")[-8000:],
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "rc": 124,
            "stdout": str(exc.stdout or "")[-16000:],
            "stderr": str(exc.stderr or "")[-8000:],
            "timeout": True,
        }


def main() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    marker_value = f"HOST_RUNTIME_MARKER_OK {utc_now()} pid={os.getpid()}"
    MARKER.write_text(marker_value + "\n", encoding="utf-8")

    checks = {
        "pwd": run("pwd"),
        "whoami_id": run("whoami && id && hostname"),
        "marker_cat": run(f"cat {MARKER}"),
        "openclaw_version": run("openclaw --version 2>&1 || true"),
        "openclaw_status": run("openclaw gateway status --deep 2>&1 || true"),
        "openclaw_help": run("openclaw --help 2>&1 | head -n 240 || true"),
        "openclaw_plugins_help": run("openclaw plugins --help 2>&1 | head -n 240 || true"),
        "openclaw_plugins_list": run("openclaw plugins list 2>&1 || true"),
        "openclaw_commands_help": run("openclaw commands --help 2>&1 || true"),
        "openclaw_models_auth": run("openclaw models auth 2>&1 || true"),
        "gateway_logs_tool_related": run("journalctl --user -u openclaw-gateway.service -n 260 --no-pager 2>&1 | grep -Ei 'tool|command|exec|write|file|plugin|sandbox|workspace|permission|deny|allow' | tail -n 180 || true"),
        "config_tool_related": run("grep -RInE 'commands|exec|write|file|filesystem|tool|sandbox|workspace|allow|deny|plugin' ~/.openclaw/openclaw.json ~/.openclaw/agents/main/agent 2>/dev/null | head -n 300 || true"),
        "processes": run("ps -eo pid,ppid,user,etimes,cmd | grep -E 'openclaw|node|python|uvicorn|oris_free_mesh' | grep -v grep | tail -n 120 || true"),
        "workspace_listing": run("ls -la ~/.openclaw/workspace 2>/dev/null | head -n 120 || true"),
        "projects_listing": run("ls -la /home/admin/projects | head -n 120 || true"),
    }

    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "host_marker": marker_value,
        "marker_path": str(MARKER),
        "diagnosis_goal": "Determine whether OpenClaw has real host shell/file tools or only chat-level pseudo tool traces.",
        "checks": checks,
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Host Tool Runtime Diagnostic\n\n"
        f"- ok: `true`\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- marker_path: `{MARKER}`\n"
        f"- host_marker: `{marker_value}`\n"
        "- purpose: verify whether OpenClaw exec/write tools operate on the real host filesystem\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "json_out": str(OUT_JSON), "md_out": str(OUT_MD), "marker": marker_value}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
