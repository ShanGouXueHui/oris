#!/usr/bin/env python3
"""Probe how OpenClaw resolves model providers.

This is intentionally read-only. It masks secrets and searches the local
OpenClaw install for provider/baseUrl/auth-profile resolution hints.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_provider_resolution_probe.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_provider_resolution_probe.md"
OPENCLAW_HOME = Path.home() / ".openclaw"
AGENT_DIR = OPENCLAW_HOME / "agents" / "main" / "agent"
NPM_ROOT = Path.home() / ".npm-global" / "lib" / "node_modules" / "openclaw"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{16,}"),
    re.compile(r"hf_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-.]{8,}", re.I),
    re.compile(r"apiKey=([A-Za-z0-9_\-\.]{8,})"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask(s: str) -> str:
    out = s or ""
    for pat in SECRET_PATTERNS:
        out = pat.sub(lambda m: m.group(0).split("=")[0] + "=***MASKED***" if "apiKey=" in m.group(0) else "***MASKED***", out)
    return out


def run(cmd: str, timeout: int = 25) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": mask((p.stdout or "")[-20000:]), "stderr": mask((p.stderr or "")[-8000:])}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "stdout": mask(str(exc.stdout or "")[-20000:]), "stderr": mask(str(exc.stderr or "")[-8000:])}


def load_json_masked(path: Path) -> Any:
    if not path.exists():
        return {"_exists": False, "path": str(path)}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return sanitize(raw)
    except Exception as exc:
        return {"_exists": True, "_error": repr(exc), "path": str(path)}


def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ["key", "token", "secret", "password"]):
                out[k] = "***MASKED***" if v else v
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    if isinstance(obj, str):
        return mask(obj)
    return obj


def main() -> int:
    commands = {
        "openclaw_version": "openclaw --version 2>&1 || true",
        "openclaw_help": "openclaw --help 2>&1 | head -n 200 || true",
        "openclaw_models_help": "openclaw models --help 2>&1 | head -n 200 || true",
        "openclaw_agents_help": "openclaw agents --help 2>&1 | head -n 200 || true",
        "openclaw_plugins_help": "openclaw plugins --help 2>&1 | head -n 200 || true",
        "openclaw_status": "openclaw gateway status --deep 2>&1 || true",
        "provider_code_grep": f"grep -RInE 'baseUrl|baseURL|openai-completions|openrouter|auth-profiles|provider.*openai|provider.*custom|OPENAI_BASE|apiKey' {NPM_ROOT}/dist 2>/dev/null | head -n 500 || true",
        "agent_file_grep": "grep -RInE 'openrouter|openrouter.ai|127.0.0.1:8789|baseUrl|auth-profiles|provider|apiKey' ~/.openclaw/openclaw.json ~/.openclaw/agents/main/agent 2>/dev/null | head -n 500 || true",
        "recent_gateway_errors": "journalctl --user -u openclaw-gateway.service -n 260 --no-pager 2>&1 | grep -Ei 'openrouter|billing|402|baseUrl|provider|auth|model' | tail -n 120 || true",
    }

    results = {name: run(cmd) for name, cmd in commands.items()}
    files = {
        "openclaw_json": load_json_masked(OPENCLAW_HOME / "openclaw.json"),
        "agent_models_json": load_json_masked(AGENT_DIR / "models.json"),
        "agent_auth_profiles_json": load_json_masked(AGENT_DIR / "auth-profiles.json"),
    }

    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "files": files,
        "commands": results,
        "question": "Which provider key/schema should be used for a local OpenAI-compatible Free Mesh endpoint instead of OpenClaw's official OpenRouter provider?",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Provider Resolution Probe\n\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        "- secrets: masked\n"
        "- purpose: identify effective provider resolution path for local Free Mesh bridge\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
