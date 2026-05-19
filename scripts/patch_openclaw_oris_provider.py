#!/usr/bin/env python3
"""Register ORIS Free Mesh as an OpenClaw provider/model.

OpenClaw accepts agents.defaults.models['oris/free-auto'] only when the real
provider registry also contains models.providers['oris'].models[]. This script
adds the minimal provider/model registry entry and keeps the default logical
model as oris/free-auto.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
LOGICAL_MODEL = "oris/free-auto"
PROVIDER_ID = "oris"
PROVIDER_MODEL_ID = "free-auto"
BASE_URL = "http://127.0.0.1:8789/v1"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def model_summary(data: dict[str, Any]) -> dict[str, Any]:
    agents_defaults = ((data.get("agents") or {}).get("defaults") or {})
    models_root = data.get("models") or {}
    providers = models_root.get("providers") if isinstance(models_root, dict) else None
    oris_provider = providers.get(PROVIDER_ID) if isinstance(providers, dict) else None
    return {
        "agents.defaults.model": agents_defaults.get("model"),
        "agents.defaults.models_keys": sorted((agents_defaults.get("models") or {}).keys()) if isinstance(agents_defaults.get("models"), dict) else None,
        "models.providers_keys": sorted(providers.keys()) if isinstance(providers, dict) else None,
        "models.providers.oris": oris_provider,
    }


def clean_agent_model_entries(data: dict[str, Any]) -> None:
    defaults = data.setdefault("agents", {}).setdefault("defaults", {})
    models = defaults.setdefault("models", {})
    if not isinstance(models, dict):
        models = {}
        defaults["models"] = models
    if "openrouter/auto" in models:
        old = models.get("openrouter/auto") if isinstance(models.get("openrouter/auto"), dict) else {}
        models["openrouter/auto"] = {"alias": old.get("alias", "OpenRouter")}
    models[LOGICAL_MODEL] = {"alias": "ORIS Free Mesh"}
    model = defaults.setdefault("model", {})
    if not isinstance(model, dict):
        model = {}
        defaults["model"] = model
    model["primary"] = LOGICAL_MODEL


def ensure_oris_provider(data: dict[str, Any]) -> None:
    models_root = data.setdefault("models", {})
    if not isinstance(models_root, dict):
        models_root = {}
        data["models"] = models_root
    providers = models_root.setdefault("providers", {})
    if not isinstance(providers, dict):
        providers = {}
        models_root["providers"] = providers

    provider = providers.setdefault(PROVIDER_ID, {})
    if not isinstance(provider, dict):
        provider = {}
        providers[PROVIDER_ID] = provider

    provider.setdefault("provider", "openai-compatible")
    provider.setdefault("baseURL", BASE_URL)
    provider.setdefault("apiBase", BASE_URL)
    provider.setdefault("auth", {"type": "bearer", "keyRef": "/services/oris_api/bearerToken"})

    models = provider.setdefault("models", [])
    if not isinstance(models, list):
        models = []
        provider["models"] = models
    if not any(isinstance(item, dict) and item.get("id") == PROVIDER_MODEL_ID for item in models):
        models.append({"id": PROVIDER_MODEL_ID, "alias": "ORIS Free Mesh"})


def patch_config(data: dict[str, Any]) -> dict[str, Any]:
    clean_agent_model_entries(data)
    ensure_oris_provider(data)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Register ORIS Free Mesh provider model in OpenClaw config.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not CONFIG_PATH.exists():
        print(json.dumps({"ok": False, "error": "openclaw_config_not_found", "path": str(CONFIG_PATH)}, ensure_ascii=False, indent=2))
        return 1

    before = load_json(CONFIG_PATH)
    after = patch_config(json.loads(json.dumps(before)))
    backup_path = Path("/tmp") / f"openclaw.json.oris-provider.backup.{utc_stamp()}"
    result = {
        "ok": True,
        "apply": args.apply,
        "config_path": str(CONFIG_PATH),
        "backup_path": str(backup_path),
        "before": model_summary(before),
        "after": model_summary(after),
    }
    if args.apply:
        shutil.copy2(CONFIG_PATH, backup_path)
        save_json(CONFIG_PATH, after)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
