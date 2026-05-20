#!/usr/bin/env python3
"""Bridge OpenClaw's native openrouter/auto model to ORIS Free Mesh.

Why this exists:
- OpenClaw already understands provider=openrouter and model=openrouter/auto.
- Custom provider schemas are strict and should not be guessed.
- This patch keeps OpenClaw schema-native keys, but points the provider baseUrl
  to local ORIS Free Mesh API, so real model choice remains owned by ORIS
  runtime_plan and failover chain.

No secrets are printed. The ORIS API bearer token is copied from
~/.openclaw/secrets.json into the local agent model catalog apiKey field.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_MODELS_PATH = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "models.json"
OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
PROVIDER_ID = "openrouter"
MODEL_KEY = "openrouter/auto"
MODEL_ID = "auto"
FREE_MESH_BASE_URL = "http://127.0.0.1:8789/v1"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_oris_token() -> str:
    data = load_json(SECRETS_PATH)
    token = (((data.get("services") or {}).get("oris_api") or {}).get("bearerToken") or "")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("missing services.oris_api.bearerToken in ~/.openclaw/secrets.json")
    return token.strip()


def patch_agent_models(data: dict[str, Any], token: str) -> dict[str, Any]:
    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        providers = {}
        data["providers"] = providers
    provider = providers.setdefault(PROVIDER_ID, {})
    if not isinstance(provider, dict):
        provider = {}
        providers[PROVIDER_ID] = provider

    provider["baseUrl"] = FREE_MESH_BASE_URL
    provider["api"] = "openai-completions"
    provider["apiKey"] = token

    models = provider.setdefault("models", [])
    if not isinstance(models, list):
        models = []
        provider["models"] = models

    auto = None
    for item in models:
        if isinstance(item, dict) and item.get("id") == MODEL_ID:
            auto = item
            break
    if auto is None:
        auto = {"id": MODEL_ID}
        models.insert(0, auto)

    auto.update(
        {
            "id": MODEL_ID,
            "name": "ORIS Free Mesh Auto",
            "reasoning": False,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 200000,
            "maxTokens": 4096,
        }
    )
    return data


def patch_openclaw_default(data: dict[str, Any]) -> dict[str, Any]:
    # Remove invalid custom provider block if a previous attempt left it behind.
    root_models = data.get("models")
    if isinstance(root_models, dict):
        providers = root_models.get("providers")
        if isinstance(providers, dict):
            providers.pop("oris", None)

    defaults = data.setdefault("agents", {}).setdefault("defaults", {})
    models = defaults.setdefault("models", {})
    if not isinstance(models, dict):
        models = {}
        defaults["models"] = models
    models[MODEL_KEY] = {"alias": "ORIS Free Mesh"}
    models.pop("oris/free-auto", None)

    model = defaults.setdefault("model", {})
    if not isinstance(model, dict):
        model = {}
        defaults["model"] = model
    model["primary"] = MODEL_KEY
    return data


def summarize(agent_models: dict[str, Any], openclaw_config: dict[str, Any]) -> dict[str, Any]:
    providers = agent_models.get("providers") if isinstance(agent_models.get("providers"), dict) else {}
    provider = providers.get(PROVIDER_ID) if isinstance(providers, dict) else None
    defaults = ((openclaw_config.get("agents") or {}).get("defaults") or {})
    auto = None
    if isinstance(provider, dict):
        for item in provider.get("models", []) if isinstance(provider.get("models"), list) else []:
            if isinstance(item, dict) and item.get("id") == MODEL_ID:
                auto = item
                break
    return {
        "agent_models_path": str(AGENT_MODELS_PATH),
        "openclaw_config_path": str(OPENCLAW_CONFIG_PATH),
        "provider": PROVIDER_ID,
        "provider_baseUrl": provider.get("baseUrl") if isinstance(provider, dict) else None,
        "provider_api": provider.get("api") if isinstance(provider, dict) else None,
        "provider_has_apiKey": bool(provider.get("apiKey")) if isinstance(provider, dict) else False,
        "auto_model": {k: v for k, v in (auto or {}).items() if k != "apiKey"},
        "primary_model": ((defaults.get("model") or {}).get("primary")) if isinstance(defaults.get("model"), dict) else None,
        "default_model_keys": sorted((defaults.get("models") or {}).keys()) if isinstance(defaults.get("models"), dict) else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge OpenClaw openrouter/auto to ORIS Free Mesh API.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    token = read_oris_token()
    agent_before = load_json(AGENT_MODELS_PATH)
    cfg_before = load_json(OPENCLAW_CONFIG_PATH)
    agent_after = patch_agent_models(json.loads(json.dumps(agent_before)), token)
    cfg_after = patch_openclaw_default(json.loads(json.dumps(cfg_before)))
    backup_dir = Path("/tmp") / f"openclaw-openrouter-free-mesh-{stamp()}"

    result = {
        "ok": True,
        "apply": args.apply,
        "backup_dir": str(backup_dir),
        "before": summarize(agent_before, cfg_before),
        "after": summarize(agent_after, cfg_after),
        "routing_principle": "OpenClaw uses schema-native openrouter/auto, but provider baseUrl points to ORIS Free Mesh; real model selection is owned by ORIS runtime_plan.",
    }
    if args.apply:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(AGENT_MODELS_PATH, backup_dir / "models.json.before")
        shutil.copy2(OPENCLAW_CONFIG_PATH, backup_dir / "openclaw.json.before")
        save_json(AGENT_MODELS_PATH, agent_after)
        save_json(OPENCLAW_CONFIG_PATH, cfg_after)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
