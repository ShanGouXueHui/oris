#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.compiler_compare_engine import build_compare_bundle, load_json

BASE_COMPILER = ROOT / "scripts" / "prompt_to_case_compiler.py"
RUNTIME_PATH = ROOT / "config" / "insight_compiler_runtime.json"
REGISTRY_PATH = ROOT / "config" / "external_skill_registry.json"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-text", required=True)
    args, unknown = ap.parse_known_args()

    cmd = ["/usr/bin/python3", str(BASE_COMPILER), "--prompt-text", args.prompt_text] + unknown
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or r.stdout or "")
        raise SystemExit(r.returncode)

    try:
        base_case = json.loads(r.stdout)
    except Exception:
        sys.stderr.write((r.stdout or "")[-4000:])
        raise SystemExit(2)

    runtime_cfg = (load_json(RUNTIME_PATH, {}) or {}).get("compiler_runtime") or {}
    registry_cfg = load_json(REGISTRY_PATH, {}) or {}

    compare_bundle = build_compare_bundle(
        prompt_text=args.prompt_text,
        base_case=base_case,
        runtime_cfg=runtime_cfg,
        registry_cfg=registry_cfg
    )

    trace = list(base_case.get("trace_stages") or [])
    for x in compare_bundle.get("trace_appends") or []:
        if x not in trace:
            trace.append(x)

    base_case["parser_mode"] = compare_bundle.get("parser_mode")
    base_case["execution_mode"] = compare_bundle.get("execution_mode")
    base_case["trace_stages"] = trace
    base_case["llm_compare"] = compare_bundle.get("llm_compare")
    base_case["compare_summary"] = compare_bundle.get("compare_summary")
    base_case["external_skill_candidates"] = compare_bundle.get("external_skill_candidates")
    base_case["evolution_actions"] = compare_bundle.get("evolution_actions")

    compiled_case_path = base_case.get("compiled_case_path")
    if compiled_case_path:
        p = Path(compiled_case_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(base_case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(base_case, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
