#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "orchestration" / "provider_registry.json"
SNAPSHOT_PATH = ROOT / "orchestration" / "provider_health_snapshot.json"
POLICY_PATH = ROOT / "orchestration" / "routing_policy.yaml"
ACTIVE_PATH = ROOT / "orchestration" / "active_routing.json"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def simple_yaml_parse(path: Path) -> dict:
    """
    Lightweight parser for the constrained routing_policy.yaml currently used here.
    Avoids adding a PyYAML dependency.
    """
    text = path.read_text(encoding="utf-8").splitlines()
    data = {"roles": {}, "global": {}, "replacement_policy": {}}

    section = None
    current_role = None
    in_candidates = False

    for raw in text:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        if line.startswith("global:"):
            section = "global"
            current_role = None
            in_candidates = False
            continue
        if line.startswith("roles:"):
            section = "roles"
            current_role = None
            in_candidates = False
            continue
        if line.startswith("replacement_policy:"):
            section = "replacement_policy"
            current_role = None
            in_candidates = False
            continue

        if section == "roles" and line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current_role = line.strip()[:-1]
            data["roles"][current_role] = {"ordered_candidates": [], "rules": {}}
            in_candidates = False
            continue

        if section == "roles" and current_role:
            if line.strip() == "ordered_candidates:":
                in_candidates = True
                continue
            if line.strip() == "rules:":
                in_candidates = False
                continue
            if in_candidates and line.strip().startswith("- "):
                data["roles"][current_role]["ordered_candidates"].append(line.strip()[2:].strip())
                continue

    return data

def health_by_provider(snapshot: dict) -> dict:
    out = {}
    for p in snapshot.get("providers", []):
        out[p.get("provider_id")] = p
    return out

def index_models(registry: dict, snapshot_idx: dict) -> dict:
    catalog = {}
    for provider in registry.get("providers", []):
        provider_id = provider.get("provider_id")
        provider_health = snapshot_idx.get(provider_id, {})
        provider_status = provider_health.get("status", provider.get("health", {}).get("status", "unknown"))

        model_health_map = {}
        for m in provider_health.get("models", []):
            model_health_map[m.get("model_id")] = m

        for model in provider.get("models", []):
            model_id = model.get("model_id")
            model_probe = model_health_map.get(model_id, {})
            catalog[model_id] = {
                "provider_id": provider_id,
                "provider_enabled": provider.get("enabled", False),
                "provider_status": provider_status,
                "model_id": model_id,
                "free_candidate": model.get("free_candidate", False),
                "priority": model.get("priority", 0),
                "role_tags": model.get("role_tags", []),
                "probe_result": model_probe.get("probe_result"),
                "latency_ms": model_probe.get("latency_ms"),
                "error": model_probe.get("error"),
                "notes": model.get("notes"),
            }
    return catalog

def model_allowed(model: dict, role_rules: dict) -> bool:
    if not model:
        return False
    if not model.get("provider_enabled", False):
        return False

    allowed_statuses = role_rules.get("require_health_status", ["healthy", "degraded", "unknown"])
    if model.get("provider_status") not in allowed_statuses:
        return False

    avoid_status = role_rules.get("avoid_status", [])
    if model.get("provider_status") in avoid_status:
        return False

    if role_rules.get("allow_free_candidates_only", False) and not model.get("free_candidate", False):
        return False

    return True

def choose_role_targets(policy: dict, catalog: dict) -> dict:
    decisions = {}
    roles = policy.get("roles", {})

    for role_name, role_cfg in roles.items():
        ordered = role_cfg.get("ordered_candidates", [])
        rules = role_cfg.get("rules", {})

        selected = None
        considered = []

        for candidate in ordered:
            model = catalog.get(candidate)
            considered.append({
                "model_id": candidate,
                "exists": bool(model),
                "provider_status": model.get("provider_status") if model else None,
                "provider_enabled": model.get("provider_enabled") if model else None,
                "free_candidate": model.get("free_candidate") if model else None,
                "accepted": model_allowed(model, rules) if model else False,
            })
            if model and model_allowed(model, rules):
                selected = model
                break

        if not selected:
            fallback_candidates = []
            for model_id, model in catalog.items():
                if model_allowed(model, rules):
                    fallback_candidates.append(model)

            fallback_candidates.sort(
                key=lambda x: (
                    0 if x.get("provider_status") == "healthy" else 1,
                    0 if x.get("free_candidate") else 1,
                    -int(x.get("priority", 0)),
                    x.get("model_id", "")
                )
            )
            if fallback_candidates:
                selected = fallback_candidates[0]

        decisions[role_name] = {
            "selected_model": selected.get("model_id") if selected else None,
            "provider_id": selected.get("provider_id") if selected else None,
            "provider_status": selected.get("provider_status") if selected else None,
            "free_candidate": selected.get("free_candidate") if selected else None,
            "selection_mode": (
                "ordered_candidates" if selected and selected.get("model_id") in ordered
                else "fallback_scan" if selected
                else "no_match"
            ),
            "considered": considered,
        }

    return decisions

def main() -> int:
    registry = load_json(REGISTRY_PATH)
    snapshot = load_json(SNAPSHOT_PATH)
    policy = simple_yaml_parse(POLICY_PATH)

    snapshot_idx = health_by_provider(snapshot)
    catalog = index_models(registry, snapshot_idx)
    decisions = choose_role_targets(policy, catalog)

    active = {
        "version": 1,
        "generated_at": utc_now(),
        "source_files": {
            "registry": str(REGISTRY_PATH),
            "snapshot": str(SNAPSHOT_PATH),
            "policy": str(POLICY_PATH),
        },
        "decisions": decisions,
    }

    with ACTIVE_PATH.open("w", encoding="utf-8") as f:
        json.dump(active, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("model_selector: active routing updated")
    print(f"model_selector: wrote -> {ACTIVE_PATH}")
    for role, info in decisions.items():
        print(f"{role}: {info['selected_model']} ({info['selection_mode']})")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
