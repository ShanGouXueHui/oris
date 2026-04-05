#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "orchestration" / "provider_registry.json"
SNAPSHOT_PATH = ROOT / "orchestration" / "provider_health_snapshot.json"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def build_snapshot(registry: dict) -> dict:
    items = []
    for provider in registry.get("providers", []):
        items.append(
            {
                "provider_id": provider.get("provider_id"),
                "enabled": provider.get("enabled", False),
                "status": provider.get("health", {}).get("status", "unknown"),
                "last_probe_at": utc_now(),
                "models": [
                    {
                        "model_id": model.get("model_id"),
                        "free_candidate": model.get("free_candidate", False),
                        "probe_result": "not_implemented",
                        "latency_ms": None,
                        "error": None,
                    }
                    for model in provider.get("models", [])
                ],
            }
        )
    return {
        "version": 1,
        "generated_at": utc_now(),
        "providers": items,
    }

def main() -> int:
    registry = load_json(REGISTRY_PATH)
    registry["updated_at"] = utc_now()
    save_json(REGISTRY_PATH, registry)

    snapshot = build_snapshot(registry)
    save_json(SNAPSHOT_PATH, snapshot)

    print("quota_probe: registry refreshed")
    print(f"quota_probe: wrote snapshot -> {SNAPSHOT_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
