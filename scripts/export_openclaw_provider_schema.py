#!/usr/bin/env python3
"""Export redacted OpenClaw model provider schema.

This script reads ~/.openclaw/openclaw.json and writes a redacted schema sample
for models.providers and agents.defaults. It does not modify OpenClaw config.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
OUT_JSON = Path("logs/dev_employee/latest_openclaw_provider_schema.json")
OUT_MD = Path("logs/dev_employee/latest_openclaw_provider_schema.md")
SECRET_WORDS = ("key", "token", "secret", "password", "credential")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def redact(value: Any, key: str = "") -> Any:
    if any(word in key.lower() for word in SECRET_WORDS):
        return "***MASKED***" if value is not None else None
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    return value


def main() -> int:
    if not CONFIG_PATH.exists():
        payload = {"ok": False, "error": "openclaw_config_not_found", "path": str(CONFIG_PATH)}
    else:
        cfg = load_json(CONFIG_PATH)
        agents_defaults = ((cfg.get("agents") or {}).get("defaults") or {})
        models_root = cfg.get("models") or {}
        providers = models_root.get("providers") if isinstance(models_root, dict) else None
        auth_profiles = ((cfg.get("auth") or {}).get("profiles") or {})
        payload = {
            "ok": True,
            "generated_at": utc_now(),
            "config_path": str(CONFIG_PATH),
            "top_level_keys": sorted(cfg.keys()),
            "agents_defaults": redact(agents_defaults),
            "models_root_keys": sorted(models_root.keys()) if isinstance(models_root, dict) else None,
            "models_providers_type": type(providers).__name__,
            "models_providers_keys": sorted(providers.keys()) if isinstance(providers, dict) else [],
            "models_providers_redacted": redact(providers) if isinstance(providers, dict) else providers,
            "auth_profiles_keys": sorted(auth_profiles.keys()) if isinstance(auth_profiles, dict) else [],
            "auth_profiles_redacted": redact(auth_profiles) if isinstance(auth_profiles, dict) else auth_profiles,
        }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# OpenClaw Provider Schema Export",
        "",
        f"- generated_at: `{payload.get('generated_at')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- models_providers_type: `{payload.get('models_providers_type')}`",
        f"- models_providers_keys: `{payload.get('models_providers_keys')}`",
        f"- auth_profiles_keys: `{payload.get('auth_profiles_keys')}`",
        "",
        f"See JSON: `{OUT_JSON}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": payload.get("ok"), "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
