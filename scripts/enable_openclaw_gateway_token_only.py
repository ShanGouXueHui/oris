#!/usr/bin/env python3
"""Enable OpenClaw gateway token-only auth.

Keeps Nginx Basic Auth disabled and disables device pairing by not enabling the
pairing-based auth mode. Restores a schema-valid gateway.auth object from the
most recent token-auth backup when possible; otherwise writes {mode: token}.
No secret value is printed.
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
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_gateway_token_only.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_gateway_token_only.md"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(cmd: str, timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": (p.stdout or "")[-8000:], "stderr": (p.stderr or "")[-4000:]}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "stdout": str(exc.stdout or "")[-8000:], "stderr": str(exc.stderr or "")[-4000:]}


def load(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


def auth_from(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    data = load(path)
    if not data:
        return None, None
    auth = ((data.get("gateway") or {}).get("auth") or {})
    if not isinstance(auth, dict):
        return None, None
    if auth.get("mode") == "token" or "token" in auth:
        cleaned = {k: v for k, v in auth.items() if k not in {"devicePairing", "pairing", "requireDeviceApproval", "requireDevicePairing"}}
        cleaned["mode"] = "token"
        return cleaned, str(path)
    return None, None


def find_token_auth() -> tuple[dict[str, Any], str]:
    candidates = [CONFIG]
    candidates.extend(sorted(Path("/tmp").glob("openclaw.json.before*"), key=lambda p: p.stat().st_mtime, reverse=True))
    candidates.extend(sorted(Path("/tmp").glob("**/openclaw.json.before"), key=lambda p: p.stat().st_mtime, reverse=True))
    candidates.extend(sorted(Path.home().glob(".openclaw/**/*.bak"), key=lambda p: p.stat().st_mtime, reverse=True))
    seen: set[str] = set()
    for path in candidates:
        sp = str(path)
        if sp in seen or not path.exists() or not path.is_file():
            continue
        seen.add(sp)
        auth, source = auth_from(path)
        if auth:
            return auth, source or sp
    return {"mode": "token"}, "fallback_mode_token_only"


def main() -> int:
    ts = stamp()
    backup = Path("/tmp") / f"openclaw.json.before-token-only.{ts}"
    data = load(CONFIG)
    if data is None:
        raise SystemExit(f"invalid json: {CONFIG}")
    shutil.copy2(CONFIG, backup)

    data.pop("_oris_auth_test_note", None)
    gateway = data.setdefault("gateway", {})
    if not isinstance(gateway, dict):
        gateway = {}
        data["gateway"] = gateway
    auth, source = find_token_auth()
    gateway["auth"] = auth
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    restart = run("systemctl --user restart openclaw-gateway.service && sleep 8", timeout=30)
    active = run("systemctl --user is-active openclaw-gateway.service", timeout=10)
    status = run("openclaw gateway status --deep", timeout=25)
    head = run("curl -I --max-time 8 https://control.orisfy.com/ 2>&1", timeout=12)
    logs = run("journalctl --user -u openclaw-gateway.service -n 120 --no-pager", timeout=15)

    public_head = (head.get("stdout") or "") + (head.get("stderr") or "")
    has_www_auth = "www-authenticate:" in public_head.lower()
    status_text = (status.get("stdout") or "") + (status.get("stderr") or "") + (logs.get("stdout") or "")
    token_active = "gateway.auth.token is active" in status_text or "auth.mode is \"token\"" in status_text or "auth mode=token" in status_text
    pairing_required_seen = "device pairing required" in status_text.lower()
    ok = active.get("stdout", "").strip() == "active" and not has_www_auth and token_active

    payload = {
        "ok": ok,
        "timestamp_utc": ts,
        "config_path": str(CONFIG),
        "backup_path": str(backup),
        "auth_source": source,
        "gateway_auth_mode": "token",
        "gateway_auth_has_token_field": "token" in auth,
        "restart_rc": restart.get("rc"),
        "active": active.get("stdout", "").strip(),
        "has_www_authenticate": has_www_auth,
        "token_active_detected": token_active,
        "pairing_required_seen": pairing_required_seen,
        "status": status,
        "public_head": public_head[-5000:],
        "recent_gateway_logs": logs,
        "note": "Gateway token-only auth enabled. Nginx Basic Auth remains disabled; device pairing should not be used for this test mode.",
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Gateway Token Only\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- timestamp_utc: `{ts}`\n"
        f"- active: `{payload['active']}`\n"
        f"- gateway_auth_mode: `token`\n"
        f"- token_active_detected: `{token_active}`\n"
        f"- has_www_authenticate: `{has_www_auth}`\n"
        f"- pairing_required_seen: `{pairing_required_seen}`\n"
        f"- auth_source: `{source}`\n"
        f"- backup_path: `{backup}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": ok, "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
