#!/usr/bin/env python3
"""Force OpenClaw's schema-native openrouter/auto model to use ORIS Free Mesh.

This repairs cases where OpenClaw falls back to the public OpenRouter endpoint
and returns billing errors. It keeps the OpenClaw-visible model as
openrouter/auto, but routes provider calls to the local OpenAI-compatible Free
Mesh API at 127.0.0.1:8789.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT_MODELS = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "models.json"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
SECRETS = Path.home() / ".openclaw" / "secrets.json"
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_free_mesh_bridge_repair.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_free_mesh_bridge_repair.md"
FREE_MESH_BASE = "http://127.0.0.1:8789/v1"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(cmd: str, timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": (p.stdout or "")[-8000:], "stderr": (p.stderr or "")[-4000:]}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "stdout": str(exc.stdout or "")[-8000:], "stderr": str(exc.stderr or "")[-4000:]}


def load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be object")
    return raw


def save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_oris_token() -> str:
    data = load(SECRETS)
    token = (((data.get("services") or {}).get("oris_api") or {}).get("bearerToken") or "")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("missing services.oris_api.bearerToken")
    return token.strip()


def patch_openclaw_config() -> dict[str, Any]:
    data = load(OPENCLAW_CONFIG)
    defaults = data.setdefault("agents", {}).setdefault("defaults", {})
    model_map = defaults.setdefault("models", {})
    if not isinstance(model_map, dict):
        model_map = {}
        defaults["models"] = model_map
    # Remove stale custom ORIS logical model reference that OpenClaw cannot resolve.
    model_map.pop("oris/free-auto", None)
    model_map["openrouter/auto"] = {"alias": "ORIS Free Mesh"}
    defaults.setdefault("model", {})["primary"] = "openrouter/auto"
    save(OPENCLAW_CONFIG, data)
    return {
        "primary": defaults.get("model", {}).get("primary"),
        "model_keys": sorted(model_map.keys()),
    }


def patch_agent_models(token: str) -> dict[str, Any]:
    data = load(AGENT_MODELS)
    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        providers = {}
        data["providers"] = providers
    providers.pop("oris", None)
    openrouter = providers.setdefault("openrouter", {})
    if not isinstance(openrouter, dict):
        openrouter = {}
        providers["openrouter"] = openrouter
    openrouter["baseUrl"] = FREE_MESH_BASE
    openrouter["api"] = "openai-completions"
    openrouter["apiKey"] = token
    models = openrouter.setdefault("models", [])
    if not isinstance(models, list):
        models = []
        openrouter["models"] = models
    auto = next((m for m in models if isinstance(m, dict) and m.get("id") == "auto"), None)
    if auto is None:
        auto = {"id": "auto"}
        models.insert(0, auto)
    auto.update({
        "id": "auto",
        "name": "ORIS Free Mesh Auto",
        "reasoning": False,
        "input": ["text"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": 200000,
        "maxTokens": 4096,
    })
    save(AGENT_MODELS, data)
    return {
        "baseUrl": openrouter.get("baseUrl"),
        "api": openrouter.get("api"),
        "has_apiKey": bool(openrouter.get("apiKey")),
        "auto_model": {k: v for k, v in auto.items() if k != "apiKey"},
    }


def main() -> int:
    ts = stamp()
    backup_dir = Path("/tmp") / f"openclaw-free-mesh-bridge-repair-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OPENCLAW_CONFIG, backup_dir / "openclaw.json.before")
    shutil.copy2(AGENT_MODELS, backup_dir / "agent-models.json.before")

    token = read_oris_token()
    config_summary = patch_openclaw_config()
    provider_summary = patch_agent_models(token)

    mesh_health = run("curl -sS --max-time 8 http://127.0.0.1:8789/v1/health", timeout=10)
    restart = run("systemctl --user restart openclaw-gateway.service && sleep 8", timeout=30)
    active = run("systemctl --user is-active openclaw-gateway.service", timeout=10)
    status = run("openclaw gateway status --deep", timeout=25)
    logs = run("journalctl --user -u openclaw-gateway.service -n 160 --no-pager", timeout=15)
    probe = run("cd ~/projects/oris && python3 scripts/probe_oris_free_mesh_api.py", timeout=120)

    ok = (
        active.get("stdout", "").strip() == "active"
        and provider_summary.get("baseUrl") == FREE_MESH_BASE
        and mesh_health.get("rc") == 0
        and probe.get("rc") == 0
    )

    payload = {
        "ok": ok,
        "timestamp_utc": ts,
        "backup_dir": str(backup_dir),
        "openclaw_config": config_summary,
        "openrouter_provider": provider_summary,
        "free_mesh_health": mesh_health,
        "restart": restart,
        "active": active.get("stdout", "").strip(),
        "status": status,
        "free_mesh_probe": probe,
        "recent_gateway_logs": logs,
        "decision": "OpenClaw-visible openrouter/auto is forced to local ORIS Free Mesh baseUrl to avoid public OpenRouter billing errors.",
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Free Mesh Bridge Repair\n\n"
        f"- ok: `{ok}`\n"
        f"- timestamp_utc: `{ts}`\n"
        f"- active: `{payload['active']}`\n"
        f"- primary: `{config_summary.get('primary')}`\n"
        f"- openrouter_baseUrl: `{provider_summary.get('baseUrl')}`\n"
        f"- has_apiKey: `{provider_summary.get('has_apiKey')}`\n"
        f"- backup_dir: `{backup_dir}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": ok, "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
