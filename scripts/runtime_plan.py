#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PATH = ROOT / "orchestration" / "active_routing.json"
SCOREBOARD_PATH = ROOT / "orchestration" / "provider_scoreboard.json"
REGISTRY_PATH = ROOT / "orchestration" / "provider_registry.json"
POLICY_PATH = ROOT / "orchestration" / "runtime_policy.yaml"
STATE_PATH = ROOT / "orchestration" / "runtime_state.json"
PLAN_PATH = ROOT / "orchestration" / "runtime_plan.json"
FREE_ELIGIBILITY_PATH = ROOT / "orchestration" / "free_eligibility.json"

def utc_now():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.isoformat()

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def parse_simple_yaml(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    data = {"defaults": {}, "roles": {}}
    section = None
    current_role = None

    for raw in lines:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        if line.startswith("defaults:"):
            section = "defaults"
            current_role = None
            continue

        if line.startswith("roles:"):
            section = "roles"
            current_role = None
            continue

        if section == "defaults" and line.startswith("  ") and ":" in line:
            k, v = line.strip().split(":", 1)
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                vals = [x.strip() for x in v[1:-1].split(",") if x.strip()]
                data["defaults"][k] = [int(x) for x in vals]
            else:
                data["defaults"][k] = int(v) if v.isdigit() else v
            continue

        if section == "roles" and line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current_role = line.strip()[:-1]
            data["roles"][current_role] = {}
            continue

        if section == "roles" and current_role and line.startswith("    ") and ":" in line:
            k, v = line.strip().split(":", 1)
            v = v.strip()
            data["roles"][current_role][k] = int(v) if v.isdigit() else v
            continue

    return data

def scoreboard_index(scoreboard):
    providers = {}
    models = {}
    for provider in scoreboard.get("providers", []):
        pid = provider.get("provider_id")
        providers[pid] = provider
        for model in provider.get("models", []):
            models[model.get("model_id")] = {
                "provider_id": pid,
                "provider_score": provider.get("provider_score", 0),
                "model_score": model.get("score", 0),
                "free_candidate": model.get("free_candidate", False),
                "probe_result": model.get("probe_result"),
                "error": model.get("error"),
            }
    return providers, models

def registry_role_tags(registry):
    out = {}
    for provider in registry.get("providers", []):
        for model in provider.get("models", []):
            out[model.get("model_id")] = model.get("role_tags", [])
    return out

def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None

def model_runtime_penalty(model_id, state, defaults):
    meta = (state.get("models") or {}).get(model_id) or {}
    failures = int(meta.get("consecutive_failures", 0))
    degrade = int(defaults.get("degrade_score_on_failure", 15))
    block_after = int(defaults.get("block_after_consecutive_failures", 3))

    blocked_until = parse_iso(meta.get("blocked_until"))
    now = utc_now()
    blocked = False

    if blocked_until and blocked_until > now:
        blocked = True
    elif failures >= block_after:
        blocked = True

    penalty = failures * degrade
    return penalty, blocked, failures, meta.get("blocked_until")

def role_affinity_adjustment(role_name, model_id, provider_id, role_tags):
    score = 0
    lower = (model_id or "").lower()
    tags = set(role_tags or [])

    is_coder = ("coder" in lower) or ("coding" in tags)
    is_general = ("general" in tags) or ("fallback" in tags)
    is_free = ("free_pool_candidate" in tags)
    is_cn_provider = provider_id in {"alibaba_bailian", "tencent_hunyuan", "zhipu"}

    if role_name == "coding":
        if is_coder:
            score += 25
        else:
            score -= 8

    elif role_name in {"primary_general", "report_generation", "free_fallback"}:
        if is_coder:
            score -= 18
        if is_general:
            score += 10
        if is_free:
            score += 4

    elif role_name == "cn_candidate_pool":
        if is_cn_provider:
            score += 20
        if is_coder:
            score -= 12
        if is_free:
            score += 4

    return score

def build_model_index(scoreboard, registry):
    _, model_index = scoreboard_index(scoreboard)
    tag_index = registry_role_tags(registry)

    out = {}
    for model_id, meta in model_index.items():
        out[model_id] = {
            **meta,
            "role_tags": tag_index.get(model_id, []),
        }
    return out

def eligible_for_role(role_name, model_id, verified_free_models, role_rules=None):
    role_rules = role_rules or {}
    if role_rules.get("allow_free_candidates_only", False):
        return model_id in verified_free_models
    if role_name == "free_fallback":
        return model_id in verified_free_models
    return True

def pick_fallback_chain(role_name, active, model_index, policy, state, verified_free_models):
    role_cfg = ((policy.get("roles") or {}).get(role_name) or {})
    role_rules = role_cfg.get("rules") or {}
    defaults = policy.get("defaults", {})
    role_cfg = (policy.get("roles") or {}).get(role_name, {})
    retry_attempts = role_cfg.get("retry_attempts", defaults.get("retry_attempts", 1))
    max_failover_hops = role_cfg.get("max_failover_hops", defaults.get("max_failover_hops", 3))
    backoff = defaults.get("retry_backoff_seconds", [1, 2])

    selected = (((active.get("decisions") or {}).get(role_name) or {}).get("selected_model"))
    all_models = []

    for model_id, meta in model_index.items():
        if not eligible_for_role(role_name, model_id, verified_free_models, role_rules):
            continue

        penalty, blocked, failures, blocked_until = model_runtime_penalty(model_id, state, defaults)
        affinity = role_affinity_adjustment(
            role_name,
            model_id,
            meta.get("provider_id"),
            meta.get("role_tags", [])
        )
        effective_score = int(meta.get("model_score", 0)) - penalty + affinity

        all_models.append({
            "model_id": model_id,
            "provider_id": meta.get("provider_id"),
            "provider_score": meta.get("provider_score", 0),
            "model_score": meta.get("model_score", 0),
            "affinity_adjustment": affinity,
            "effective_score": effective_score,
            "free_candidate": meta.get("free_candidate", False),
            "free_verified": model_id in verified_free_models,
            "blocked": blocked,
            "blocked_until": blocked_until,
            "consecutive_failures": failures,
            "role_tags": meta.get("role_tags", []),
        })

    all_models.sort(
        key=lambda x: (
            1 if x.get("blocked") else 0,
            -int(x.get("effective_score", 0)),
            -int(x.get("provider_score", 0)),
            x.get("model_id") or ""
        )
    )

    selected_entry = next((m for m in all_models if m["model_id"] == selected), None)

    failover_chain = []
    if selected_entry:
        failover_chain.append(selected_entry)

    for item in all_models:
        if len(failover_chain) >= max_failover_hops:
            break
        if item["model_id"] == selected:
            continue
        if item["blocked"]:
            continue
        failover_chain.append(item)

    execution_primary = None
    for item in failover_chain:
        if not item.get("blocked", False):
            execution_primary = item["model_id"]
            break

    return {
        "selected_model": selected,
        "selected_model_blocked": bool(selected_entry.get("blocked")) if selected_entry else False,
        "execution_primary": execution_primary,
        "retry_attempts": retry_attempts,
        "retry_backoff_seconds": backoff[:retry_attempts],
        "failover_chain": failover_chain,
    }

def main():
    active = load_json(ACTIVE_PATH)
    scoreboard = load_json(SCOREBOARD_PATH)
    registry = load_json(REGISTRY_PATH)
    policy = parse_simple_yaml(POLICY_PATH)
    state = load_json(STATE_PATH)
    free_eligibility = load_json(FREE_ELIGIBILITY_PATH)

    verified_free_models = set(free_eligibility.get("verified_free_models", []))
    model_index = build_model_index(scoreboard, registry)

    plans = {}
    for role_name in (active.get("decisions") or {}).keys():
        plans[role_name] = pick_fallback_chain(
            role_name,
            active,
            model_index,
            policy,
            state,
            verified_free_models
        )

    state["updated_at"] = iso(utc_now())
    save_json(STATE_PATH, state)

    output = {
        "version": 1,
        "generated_at": iso(utc_now()),
        "plans": plans,
    }
    save_json(PLAN_PATH, output)

    print("runtime_plan: updated")
    print(f"runtime_plan: wrote -> {PLAN_PATH}")
    for role, plan in plans.items():
        print(f"{role}: selected={plan['selected_model']} execution_primary={plan['execution_primary']} retries={plan['retry_attempts']}")

if __name__ == "__main__":
    main()
