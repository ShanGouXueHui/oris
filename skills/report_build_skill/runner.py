#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_skill_runtime import build_standard_output, load_request

DEFAULT_REQUEST = {
    "analysis_type": "company_profile",
    "target_company": "Canonical",
    "artifact_types": ["word", "excel", "ppt"]
}

SKILL_NAME = "report_build_skill"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None)
    args = ap.parse_args()

    request = load_request(args.input_file, args.input_json, DEFAULT_REQUEST)

    out = build_standard_output(
        skill_name=SKILL_NAME,
        request=request,
        conclusion="report_build_skill scaffold ready; next step is read analysis/evidence/citation inputs and assemble enterprise-grade Word/Excel/PPT deliverables.",
        core_data=[
            {"field": "analysis_type", "value_from_request": "analysis_type"},
            {"field": "target_company", "value_from_request": "target_company"},
            {"field": "artifact_types", "value_from_request": "artifact_types"}
        ],
        sources=[
            {"source_type": "analysis_run", "required": True},
            {"source_type": "evidence_item", "required": True},
            {"source_type": "citation_link", "required": True},
            {"source_type": "metric_observation", "required": True}
        ],
        facts=[
            "This scaffold assumes formal report generation must not bypass evidence and citation layers.",
            "Word/Excel/PPT are treated as coordinated business deliverables, not isolated file generators."
        ],
        inferences=[
            "Word should remain the primary formal report, Excel the evidence base, and PPT the executive storytelling layer."
        ],
        hypotheses=[
            "If report build is driven by stable evidence schema, multiple industry templates can be layered later with limited code churn."
        ],
        risks=[
            "If PPT is generated before evidence and Excel sheets stabilize, the storyline will drift from the auditable data base."
        ],
        next_steps=[
            "Bind analysis/evidence/citation inputs.",
            "Assemble Word formal report.",
            "Assemble Excel evidence workbook.",
            "Assemble executive PPT storyboard."
        ],
        source_plan=[
            {"step": 1, "action": "resolve_analysis_inputs"},
            {"step": 2, "action": "assemble_word_excel"},
            {"step": 3, "action": "assemble_ppt_storyline"}
        ],
        db_write_plan=[
            "report_artifact"
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
