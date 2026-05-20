#!/usr/bin/env python3
"""Export redacted OpenClaw agent model schema.

This script inspects ~/.openclaw/agents/main/agent/models.json and related
agent auth profile files. It does not modify configuration and masks secrets.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = Path.home() / ".openclaw" / "agents" / "main" / "agent"
MODELS_PATH = AGENT_DIR / "models.json"
AUTH_PROFILES_PATH = AGENT_DIR / "auth-profiles.json"
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_agent_model_schema.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_agent_model_schema.md"
SECRET_WORDS = ("key", "token", "secret", "password", "credential")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    if not path.exists():
        return {"_exists": False, "_path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_exists": True, "_path": str(path), "_error": repr(exc)}


def redact(value: Any, key: str = "") -> Any:
    if any(word in key.lower() for word in SECRET_WORDS):
        return "***MASKED***" if value is not None else None
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    return value


def run(cmd: str) -> dict[str, Any]:
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return {
        "rc": p.returncode,
        "stdout": (p.stdout or "")[-8000:],
        "stderr": (p.stderr or "")[-4000:],
    }


def main() -> int:
    models = load_json(MODELS_PATH)
    auth_profiles = load_json(AUTH_PROFILES_PATH)
    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "agent_dir": str(AGENT_DIR),
        "models_path": str(MODELS_PATH),
        "auth_profiles_path": str(AUTH_PROFILES_PATH),
        "models_redacted": redact(models),
        "auth_profiles_redacted": redact(auth_profiles),
        "openclaw_models_status": run("openclaw models status 2>&1 | tail -n 160"),
        "openclaw_models_list": run("openclaw models list 2>&1 | tail -n 200"),
        "openclaw_config_validate": run("openclaw config validate 2>&1 | tail -n 120"),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Agent Model Schema Export\n\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- agent_dir: `{AGENT_DIR}`\n"
        f"- models_path: `{MODELS_PATH}`\n"
        f"- auth_profiles_path: `{AUTH_PROFILES_PATH}`\n"
        f"- json: `{OUT_JSON}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
