#!/usr/bin/env python3
"""Cleanly disable OpenClaw gateway auth for temporary UI testing.

OpenClaw accepts gateway.auth.mode=none, but rejects extra keys under
`gateway.auth` and unknown root keys. This script writes the minimal valid
schema and exports a compact diagnostic artifact.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path.home() / ".openclaw" / "openclaw.json"
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_auth_disabled_clean.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_auth_disabled_clean.md"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(cmd: str, timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": (p.stdout or "")[-8000:], "stderr": (p.stderr or "")[-4000:]}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "stdout": str(exc.stdout or "")[-8000:], "stderr": str(exc.stderr or "")[-4000:]}


def main() -> int:
    ts = stamp()
    backup = Path("/tmp") / f"openclaw.json.before-auth-none-clean.{ts}"
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    shutil.copy2(CONFIG, backup)

    data.pop("_oris_auth_test_note", None)
    gateway = data.setdefault("gateway", {})
    if not isinstance(gateway, dict):
        gateway = {}
        data["gateway"] = gateway
    gateway["auth"] = {"mode": "none"}
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    restart = run("systemctl --user restart openclaw-gateway.service && sleep 8", timeout=30)
    active = run("systemctl --user is-active openclaw-gateway.service", timeout=10)
    status = run("openclaw gateway status --deep", timeout=25)
    head = run("curl -I --max-time 8 https://control.orisfy.com/ 2>&1", timeout=12)
    logs = run("journalctl --user -u openclaw-gateway.service -n 120 --no-pager", timeout=15)

    public_head = (head.get("stdout") or "") + (head.get("stderr") or "")
    has_www_auth = "www-authenticate:" in public_head.lower()
    ok = active.get("stdout", "").strip() == "active" and not has_www_auth

    payload = {
        "ok": ok,
        "timestamp_utc": ts,
        "config_path": str(CONFIG),
        "backup_path": str(backup),
        "gateway_auth": {"mode": "none"},
        "restart": restart,
        "active": active.get("stdout", "").strip(),
        "status": status,
        "public_head": public_head[-5000:],
        "has_www_authenticate": has_www_auth,
        "recent_gateway_logs": logs,
        "risk": "Temporary test mode: gateway auth disabled; restore protection after UI validation.",
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Auth Disabled Clean\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- timestamp_utc: `{ts}`\n"
        f"- active: `{payload['active']}`\n"
        f"- gateway_auth: `mode=none`\n"
        f"- has_www_authenticate: `{has_www_auth}`\n"
        f"- backup_path: `{backup}`\n"
        f"- risk: temporary public control UI during testing\n",
        encoding="utf-8",
    )

    print(json.dumps({"ok": ok, "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
