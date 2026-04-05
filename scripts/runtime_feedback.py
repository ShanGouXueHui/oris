#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "orchestration" / "runtime_policy.yaml"
STATE_PATH = ROOT / "orchestration" / "runtime_state.json"

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--result", required=True, choices=["success", "failure"])
    ap.add_argument("--role", default=None)
    ap.add_argument("--error", default="")
    args = ap.parse_args()

    policy = parse_simple_yaml(POLICY_PATH)
    state = load_json(STATE_PATH)

    defaults = policy.get("defaults", {})
    block_after = int(defaults.get("block_after_consecutive_failures", 3))
    block_duration_seconds = int(defaults.get("block_duration_seconds", 1800))

    models = state.setdefault("models", {})
    meta = models.setdefault(args.model, {
        "total_successes": 0,
        "total_failures": 0,
        "consecutive_failures": 0,
        "last_result": None,
        "last_role": None,
        "last_error": None,
        "last_failure_at": None,
        "last_success_at": None,
        "blocked_until": None
    })

    now = utc_now()

    if args.result == "success":
        meta["total_successes"] = int(meta.get("total_successes", 0)) + 1
        meta["consecutive_failures"] = 0
        meta["last_result"] = "success"
        meta["last_role"] = args.role
        meta["last_error"] = None
        meta["last_success_at"] = iso(now)
        meta["blocked_until"] = None
    else:
        meta["total_failures"] = int(meta.get("total_failures", 0)) + 1
        meta["consecutive_failures"] = int(meta.get("consecutive_failures", 0)) + 1
        meta["last_result"] = "failure"
        meta["last_role"] = args.role
        meta["last_error"] = args.error or None
        meta["last_failure_at"] = iso(now)

        if int(meta["consecutive_failures"]) >= block_after:
            meta["blocked_until"] = iso(now + timedelta(seconds=block_duration_seconds))

    state["updated_at"] = iso(now)
    save_json(STATE_PATH, state)

    print("runtime_feedback: updated")
    print(json.dumps({
        "model": args.model,
        "result": args.result,
        "role": args.role,
        "state": meta
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
