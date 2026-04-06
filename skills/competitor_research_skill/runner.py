#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_skill_runtime import build_standard_output, load_request

DEFAULT_REQUEST = {
    "target_company": "Canonical",
    "competitors": ["SUSE", "Red Hat"],
    "dimensions": ["product", "pricing", "distribution", "financial"]
}

SKILL_NAME = "competitor_research_skill"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None)
    args = ap.parse_args()

    request = load_request(args.input_file, args.input_json, DEFAULT_REQUEST)

    out = build_standard_output(
        skill_name=SKILL_NAME,
        request=request,
        conclusion="competitor_research_skill scaffold ready; next step is build competitor_set/member bindings and run evidence-backed comparison across selected dimensions.",
        core_data=[
            {"field": "target_company", "value_from_request": "target_company"},
            {"field": "competitors", "value_from_request": "competitors"},
            {"field": "dimensions", "value_from_request": "dimensions"}
        ],
        sources=[
            {"source_type": "official_website", "required": True},
            {"source_type": "product_page", "required": True},
            {"source_type": "pricing_page", "required": False},
            {"source_type": "exchange_filing", "required": False}
        ],
        facts=[
            "This scaffold assumes competitor research must bind every claim to comparable evidence or metric rows.",
            "Comparison output is intended to write competitor_set and competitor_set_member before analysis_run."
        ],
        inferences=[
            "Dimension-first competitor comparison reduces drift and prevents unstructured narrative-only output."
        ],
        hypotheses=[
            "If target and peer metrics are normalized into the same metric code system, reusable matrices can be auto-generated."
        ],
        risks=[
            "Competitor labels may drift if benchmark peer vs direct competitor is not explicitly modeled in competitor_set_member."
        ],
        next_steps=[
            "Create competitor set.",
            "Collect official/product/pricing snapshots.",
            "Normalize comparable metric codes.",
            "Generate evidence-backed matrix and artifact package."
        ],
        source_plan=[
            {"step": 1, "action": "create_competitor_set"},
            {"step": 2, "action": "collect_peer_sources"},
            {"step": 3, "action": "compare_dimensions"}
        ],
        db_write_plan=[
            "competitor_set",
            "competitor_set_member",
            "source_snapshot",
            "evidence_item",
            "metric_observation",
            "citation_link",
            "analysis_run"
        ],
        artifact_plan=[
            {"artifact_type": "word", "template_code": "enterprise_report_v1"},
            {"artifact_type": "excel", "template_code": "evidence_matrix_v1"},
            {"artifact_type": "ppt", "template_code": "executive_briefing_v1"}
        ]
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
