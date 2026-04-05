#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "orchestration" / "provider_health_snapshot.json"
REGISTRY_PATH = ROOT / "orchestration" / "provider_registry.json"
SCOREBOARD_PATH = ROOT / "orchestration" / "provider_scoreboard.json"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def status_base_score(status: str) -> int:
    return {
        "healthy": 100,
        "degraded": 55,
        "unknown": 40,
        "not_configured": 10,
        "down": 0,
    }.get(status, 20)

def provider_bonus(provider_id: str) -> int:
    """
    Manual seed bonuses for now.
    Later this should be learned from rolling runtime stats.
    """
    mapping = {
        "openrouter": 8,
        "gemini": 10,
        "alibaba_bailian": 12,
        "tencent_hunyuan": 9,
        "zhipu": 2,
        "minimax": 0,
        "kimi": 0,
    }
    return mapping.get(provider_id, 0)

def model_score(provider_score: int, model: dict) -> int:
    score = provider_score

    if model.get("free_candidate"):
        score += 15

    model_id = (model.get("model_id") or "").lower()

    if "coder" in model_id:
        score += 8
    if "flash-lite" in model_id:
        score += 10
    elif "flash" in model_id:
        score += 6
    if "free" in model_id:
        score += 4
    if "pro" in model_id:
        score -= 2

    return score

def main() -> int:
    snapshot = load_json(SNAPSHOT_PATH)
    registry = load_json(REGISTRY_PATH)

    registry_by_provider = {
        p.get("provider_id"): p for p in registry.get("providers", [])
    }

    providers_out = []

    for snap_provider in snapshot.get("providers", []):
        provider_id = snap_provider.get("provider_id")
        reg_provider = registry_by_provider.get(provider_id, {})
        status = snap_provider.get("status", reg_provider.get("health", {}).get("status", "unknown"))

        pscore = status_base_score(status) + provider_bonus(provider_id)
        models_out = []

        for snap_model in snap_provider.get("models", []):
            mscore = model_score(pscore, snap_model)
            models_out.append({
                "model_id": snap_model.get("model_id"),
                "score": mscore,
                "free_candidate": snap_model.get("free_candidate", False),
                "probe_result": snap_model.get("probe_result"),
                "error": snap_model.get("error"),
            })

        models_out.sort(key=lambda x: (-int(x.get("score", 0)), x.get("model_id") or ""))

        providers_out.append({
            "provider_id": provider_id,
            "status": status,
            "enabled": snap_provider.get("enabled", False),
            "provider_score": pscore,
            "models": models_out,
        })

    providers_out.sort(key=lambda x: (-int(x.get("provider_score", 0)), x.get("provider_id") or ""))

    output = {
        "version": 1,
        "generated_at": utc_now(),
        "providers": providers_out,
    }

    save_json(SCOREBOARD_PATH, output)

    print("provider_scoreboard: updated")
    print(f"provider_scoreboard: wrote -> {SCOREBOARD_PATH}")
    for p in providers_out:
        top_model = p["models"][0]["model_id"] if p.get("models") else None
        print(f'{p["provider_id"]}: provider_score={p["provider_score"]} top_model={top_model}')

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
