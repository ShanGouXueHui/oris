#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_skill_runtime import build_standard_output, load_request

DEFAULT_REQUEST = {
    "company_name": "Canonical",
    "domain": "canonical.com",
    "region": "global"
}

SKILL_NAME = "company_profile_skill"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None)
    args = ap.parse_args()

    request = load_request(args.input_file, args.input_json, DEFAULT_REQUEST)

    out = build_standard_output(
        skill_name=SKILL_NAME,
        request=request,
        conclusion="company_profile_skill scaffold ready; next step is ingest official sources and persist company/source/evidence/metric records for the target company.",
        core_data=[
            {"field": "company_name", "value_from_request": "company_name"},
            {"field": "domain", "value_from_request": "domain"},
            {"field": "region", "value_from_request": "region"}
        ],
        sources=[
            {"source_type": "official_website", "required": True},
            {"source_type": "investor_relations", "required": True},
            {"source_type": "annual_report", "required": True},
            {"source_type": "exchange_filing", "required": False}
        ],
        facts=[
            "This scaffold enforces evidence-first company profile output.",
            "Target profile generation is expected to land company/source/source_snapshot/evidence_item/metric_observation records."
        ],
        inferences=[
            "The first production use should start from official site, IR page, and latest formal filings before adding media or research sources."
        ],
        hypotheses=[
            "If official sources are stable, company profile can become the reusable base layer for competitor research and report build."
        ],
        risks=[
            "Without source locator and citation binding, profile output may look complete but remain non-auditable."
        ],
        next_steps=[
            "Collect official pages and filings.",
            "Normalize source metadata.",
            "Extract core metrics and management statements.",
            "Generate Word/Excel/PPT artifact plan."
        ],
        source_plan=[
            {"step": 1, "action": "collect_official_sources"},
            {"step": 2, "action": "normalize_source_metadata"},
            {"step": 3, "action": "extract_evidence_and_metrics"}
        ],
        db_write_plan=[
            "company",
            "source",
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
