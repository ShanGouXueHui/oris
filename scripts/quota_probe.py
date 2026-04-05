#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "orchestration" / "provider_registry.json"
SNAPSHOT_PATH = ROOT / "orchestration" / "provider_health_snapshot.json"
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def read_openrouter_api_key() -> str | None:
    if not SECRETS_PATH.exists():
        return None
    data = load_json(SECRETS_PATH)
    return (
        (((data.get("models") or {}).get("providers") or {}).get("openrouter") or {}).get("apiKey")
    )

def fetch_openrouter_models(api_key: str) -> list[dict]:
    req = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "ORIS-Provider-Orchestration/1.0"
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("OpenRouter models API returned unexpected payload")
    return data

def is_zero_price(v) -> bool:
    try:
        return float(v) == 0.0
    except Exception:
        return False

def build_openrouter_models(remote_models: list[dict]) -> list[dict]:
    results = []

    results.append(
        {
            "model_id": "openrouter/auto",
            "role_tags": ["general", "fallback"],
            "priority": 100,
            "quota_mode": "dynamic",
            "cost_mode": "mixed",
            "free_candidate": False,
            "notes": "OpenRouter router default; actual upstream model may change."
        }
    )

    results.append(
        {
            "model_id": "openrouter/free",
            "role_tags": ["fallback", "free_pool"],
            "priority": 95,
            "quota_mode": "dynamic",
            "cost_mode": "free_or_dynamic",
            "free_candidate": True,
            "notes": "OpenRouter free router; available free models are provider-managed and dynamic."
        }
    )

    seen = {"openrouter/auto", "openrouter/free"}

    for item in remote_models:
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id or model_id in seen:
            continue

        pricing = item.get("pricing") or {}
        prompt_price = pricing.get("prompt")
        completion_price = pricing.get("completion")

        free_candidate = (
            model_id.endswith(":free")
            or model_id.startswith("openrouter/free")
            or (is_zero_price(prompt_price) and is_zero_price(completion_price))
        )

        role_tags = ["catalog_discovered"]
        if free_candidate:
            role_tags.append("free_pool_candidate")

        results.append(
            {
                "model_id": model_id,
                "role_tags": role_tags,
                "priority": 60 if free_candidate else 40,
                "quota_mode": "dynamic",
                "cost_mode": "free_or_dynamic" if free_candidate else "dynamic",
                "free_candidate": free_candidate,
                "notes": "Discovered from OpenRouter Models API."
            }
        )
        seen.add(model_id)

    results.sort(key=lambda x: (-int(bool(x.get("free_candidate"))), -int(x.get("priority", 0)), x.get("model_id", "")))
    return results

def refresh_openrouter(provider: dict) -> tuple[dict, dict]:
    now = utc_now()
    api_key = read_openrouter_api_key()
    snapshot_models = []

    if not api_key:
        provider["enabled"] = False
        provider.setdefault("health", {})
        provider["health"].update(
            {
                "status": "not_configured",
                "last_probe_at": now,
                "last_error": "missing_openrouter_api_key"
            }
        )
        return provider, {
            "provider_id": "openrouter",
            "enabled": False,
            "status": "not_configured",
            "last_probe_at": now,
            "models": []
        }

    try:
        remote_models = fetch_openrouter_models(api_key)
        managed_models = build_openrouter_models(remote_models)

        provider["enabled"] = True
        provider["region"] = "global"
        provider["auth_ref"] = "/models/providers/openrouter/apiKey"
        provider["models"] = managed_models
        provider.setdefault("health", {})
        provider["health"].update(
            {
                "status": "healthy",
                "last_probe_at": now,
                "last_error": None
            }
        )

        for model in managed_models:
            snapshot_models.append(
                {
                    "model_id": model["model_id"],
                    "free_candidate": model.get("free_candidate", False),
                    "probe_result": "catalog_sync_ok",
                    "latency_ms": None,
                    "error": None,
                }
            )

        return provider, {
            "provider_id": "openrouter",
            "enabled": True,
            "status": "healthy",
            "last_probe_at": now,
            "models": snapshot_models
        }

    except urllib.error.HTTPError as e:
        err = f"http_{e.code}"
    except urllib.error.URLError as e:
        err = f"urlerror_{e.reason}"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"

    provider.setdefault("health", {})
    provider["health"].update(
        {
            "status": "degraded",
            "last_probe_at": now,
            "last_error": err
        }
    )

    existing_models = provider.get("models", [])
    for model in existing_models:
        snapshot_models.append(
            {
                "model_id": model.get("model_id"),
                "free_candidate": model.get("free_candidate", False),
                "probe_result": "catalog_sync_failed",
                "latency_ms": None,
                "error": err,
            }
        )

    return provider, {
        "provider_id": "openrouter",
        "enabled": provider.get("enabled", False),
        "status": "degraded",
        "last_probe_at": now,
        "models": snapshot_models
    }

def passthrough_provider(provider: dict) -> tuple[dict, dict]:
    now = utc_now()
    status = provider.get("health", {}).get("status", "unknown")
    models = []
    for model in provider.get("models", []):
        models.append(
            {
                "model_id": model.get("model_id"),
                "free_candidate": model.get("free_candidate", False),
                "probe_result": "not_implemented",
                "latency_ms": None,
                "error": None,
            }
        )
    return provider, {
        "provider_id": provider.get("provider_id"),
        "enabled": provider.get("enabled", False),
        "status": status,
        "last_probe_at": now,
        "models": models
    }

def main() -> int:
    registry = load_json(REGISTRY_PATH)
    registry["updated_at"] = utc_now()

    snapshots = []
    providers = []

    for provider in registry.get("providers", []):
        provider_id = provider.get("provider_id")
        if provider_id == "openrouter":
            updated_provider, snapshot = refresh_openrouter(provider)
        else:
            updated_provider, snapshot = passthrough_provider(provider)
        providers.append(updated_provider)
        snapshots.append(snapshot)

    registry["providers"] = providers
    save_json(REGISTRY_PATH, registry)

    snapshot = {
        "version": 1,
        "generated_at": utc_now(),
        "providers": snapshots,
    }
    save_json(SNAPSHOT_PATH, snapshot)

    openrouter_count = 0
    for p in providers:
        if p.get("provider_id") == "openrouter":
            openrouter_count = len(p.get("models", []))

    print("quota_probe: registry refreshed")
    print(f"quota_probe: openrouter catalog size = {openrouter_count}")
    print(f"quota_probe: wrote snapshot -> {SNAPSHOT_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
