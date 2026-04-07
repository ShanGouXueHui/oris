#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INNER = ROOT / "scripts" / "prompt_to_case_compiler_plus.py"
POLICY_PATH = ROOT / "config" / "insight_delivery_policy.json"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))

def run_json(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip()[:4000])
    s = (r.stdout or "").strip()
    try:
        return json.loads(s)
    except Exception:
        start = s.find("{")
        end = s.rfind("}")
        if start >= 0 and end > start:
            return json.loads(s[start:end+1])
        raise

def detect_requested_artifacts(prompt_text: str, policy: dict):
    s = (prompt_text or "").strip()
    lower = s.lower()
    found = []

    kw = (policy.get("explicit_artifact_keywords") or {})
    for artifact in ["word", "ppt", "excel"]:
        vals = kw.get(artifact) or []
        for x in vals:
            if x.lower() in lower or x in s:
                found.append(artifact)
                break

    found = sorted(set(found), key=lambda x: ["word", "ppt", "excel"].index(x))
    return found

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-text", required=True)
    ap.add_argument("--write-output", action="store_true")
    args = ap.parse_args()

    policy = load_json(POLICY_PATH)
    obj = run_json([
        sys.executable,
        str(INNER),
        "--prompt-text",
        args.prompt_text,
        "--write-output"
    ])

    requested = detect_requested_artifacts(args.prompt_text, policy)
    if requested:
        delivery_mode = "artifact_bundle"
        deliverables = requested
        explicit_artifact_request = True
    else:
        delivery_mode = "chat_md"
        deliverables = ["chat_md"]
        explicit_artifact_request = False

    obj["delivery_mode"] = delivery_mode
    obj["deliverables"] = deliverables
    obj["requested_artifacts"] = requested
    obj["explicit_artifact_request"] = explicit_artifact_request
    obj["delivery_policy_snapshot"] = {
        "default_delivery_mode": policy.get("default_delivery_mode"),
        "freshness_policy": policy.get("freshness_policy") or {}
    }

    compiled_case_path = obj.get("compiled_case_path")
    if args.write_output and compiled_case_path:
        p = ROOT / compiled_case_path
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print_json(obj)

if __name__ == "__main__":
    main()
