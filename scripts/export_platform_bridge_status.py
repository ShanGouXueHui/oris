#!/usr/bin/env python3
"""Export ORIS platform bridge status.

Combines OpenClaw gateway config, Free Mesh API status, and free routing audit
into a compact GitHub-visible artifact.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_platform_bridge_status.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_platform_bridge_status.md"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
AGENT_MODELS = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "models.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: str, timeout: int = 20) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": (p.stdout or "")[-5000:], "stderr": (p.stderr or "")[-2000:], "timeout": False}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "stdout": (exc.stdout or "")[-5000:] if isinstance(exc.stdout, str) else "", "stderr": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "", "timeout": True}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception as exc:
        return {"error": repr(exc)}


def openclaw_model_summary() -> dict[str, Any]:
    cfg = load_json(OPENCLAW_CONFIG)
    agent = load_json(AGENT_MODELS)
    defaults = ((cfg.get("agents") or {}).get("defaults") or {})
    provider = ((agent.get("providers") or {}).get("openrouter") or {})
    auto_model = None
    for item in provider.get("models", []) if isinstance(provider.get("models"), list) else []:
        if isinstance(item, dict) and item.get("id") == "auto":
            auto_model = {k: v for k, v in item.items() if k != "apiKey"}
            break
    return {
        "primary_model": ((defaults.get("model") or {}).get("primary")) if isinstance(defaults.get("model"), dict) else None,
        "model_keys": sorted((defaults.get("models") or {}).keys()) if isinstance(defaults.get("models"), dict) else [],
        "openrouter_baseUrl": provider.get("baseUrl"),
        "openrouter_api": provider.get("api"),
        "openrouter_has_apiKey": bool(provider.get("apiKey")),
        "openrouter_auto_model": auto_model,
    }


def main() -> int:
    model_summary = openclaw_model_summary()
    gateway_active = run("systemctl --user is-active openclaw-gateway.service")
    mesh_active = run("systemctl --user is-active oris-free-mesh-api.service")
    mesh_probe = run("cd ~/projects/oris && python3 scripts/probe_oris_free_mesh_api.py", timeout=120)
    routing_audit = load_json(ROOT / "logs" / "dev_employee" / "latest_free_routing_audit.json")
    commercial = load_json(ROOT / "logs" / "dev_employee" / "latest_commercial_readiness.json")

    try:
        mesh_probe_json = json.loads(mesh_probe.get("stdout") or "{}")
    except Exception:
        mesh_probe_json = {}

    ok = (
        gateway_active.get("stdout", "").strip() == "active"
        and mesh_active.get("stdout", "").strip() == "active"
        and model_summary.get("primary_model") == "openrouter/auto"
        and model_summary.get("openrouter_baseUrl") == "http://127.0.0.1:8789/v1"
        and bool(mesh_probe_json.get("ok"))
        and routing_audit.get("ok") is True
    )

    payload = {
        "ok": ok,
        "generated_at": utc_now(),
        "openclaw_gateway_active": gateway_active.get("stdout", "").strip(),
        "free_mesh_api_active": mesh_active.get("stdout", "").strip(),
        "openclaw_model_summary": model_summary,
        "free_mesh_probe": mesh_probe_json,
        "free_routing_audit_ok": routing_audit.get("ok"),
        "commercial_readiness_status": commercial.get("status"),
        "commercial_readiness_ok": commercial.get("ok"),
        "design_principle": "OpenClaw uses schema-native openrouter/auto while provider baseUrl points to ORIS Free Mesh; real model selection is controlled by ORIS runtime_plan.",
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# ORIS Platform Bridge Status\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- openclaw_gateway_active: `{payload['openclaw_gateway_active']}`\n"
        f"- free_mesh_api_active: `{payload['free_mesh_api_active']}`\n"
        f"- primary_model: `{model_summary.get('primary_model')}`\n"
        f"- openrouter_baseUrl: `{model_summary.get('openrouter_baseUrl')}`\n"
        f"- free_mesh_probe_ok: `{mesh_probe_json.get('ok')}`\n"
        f"- used_model: `{(mesh_probe_json.get('oris') or {}).get('used_model')}`\n"
        f"- used_provider: `{(mesh_probe_json.get('oris') or {}).get('used_provider')}`\n"
        f"- free_routing_audit_ok: `{payload['free_routing_audit_ok']}`\n"
        f"- commercial_readiness_status: `{payload['commercial_readiness_status']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": ok, "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
