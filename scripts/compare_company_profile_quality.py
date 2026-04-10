#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def latest_one(pattern: str):
    paths = sorted(Path(".").glob(pattern))
    return paths[-1] if paths else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--company-slug", required=True)
    args = ap.parse_args()

    slug = args.company_slug
    short = slug.replace("company-profile-", "")

    bundle = latest_one(f"outputs/report_build/{slug}/*/company_profile_bundle.json")
    upgrade = latest_one(f"outputs/free_research_upgrade/{short}/*.json")

    if not bundle:
        raise SystemExit("bundle not found")
    bundle_obj = load_json(bundle)

    upgrade_obj = {}
    if upgrade and upgrade.exists():
        upgrade_obj = load_json(upgrade)

    up = upgrade_obj.get("upgrade_json") if isinstance(upgrade_obj.get("upgrade_json"), dict) else upgrade_obj

    out = {
        "company_slug": slug,
        "bundle_file": str(bundle) if bundle else None,
        "upgrade_file": str(upgrade) if upgrade else None,
        "bundle_synthesis_mode": bundle_obj.get("synthesis_mode"),
        "upgrade_used_mode": up.get("used_mode") or upgrade_obj.get("upgrade_used_mode"),
        "upgrade_llm_ok": up.get("llm_ok") if "llm_ok" in up else upgrade_obj.get("upgrade_llm_ok"),
        "exec_summary": up.get("exec_summary") or [],
        "numeric_kpis": up.get("numeric_kpis") or [],
        "gap_findings": up.get("gap_findings") or [],
        "followup_search_terms": up.get("followup_search_terms") or [],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
