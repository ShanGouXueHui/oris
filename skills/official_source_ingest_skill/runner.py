#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_skill_runtime import build_standard_output, load_request

DEFAULT_REQUEST = {
    "entity": "Canonical",
    "source_scope": ["official_website", "annual_report", "investor_relations"],
    "time_range": "latest"
}

SKILL_NAME = "official_source_ingest_skill"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None)
    args = ap.parse_args()

    request = load_request(args.input_file, args.input_json, DEFAULT_REQUEST)

    out = build_standard_output(
        skill_name=SKILL_NAME,
        request=request,
        conclusion="official_source_ingest_skill scaffold ready; next step is ingest official sources into source/source_snapshot/evidence_item/metric_observation with durable storage paths.",
        core_data=[
            {"field": "entity", "value_from_request": "entity"},
            {"field": "source_scope", "value_from_request": "source_scope"},
            {"field": "time_range", "value_from_request": "time_range"}
        ],
        sources=[
            {"source_type": "official_website", "required": True},
            {"source_type": "government", "required": False},
            {"source_type": "api", "required": False},
            {"source_type": "pdf", "required": True}
        ],
        facts=[
            "This scaffold treats official source ingest as the write entrance for source and source_snapshot.",
            "Every ingested source should preserve storage path and fetch timestamp."
        ],
        inferences=[
            "Stable official ingest is the prerequisite for evidence extraction, metric observation, and snapshot diff."
        ],
        hypotheses=[
            "If official ingest is durable, weekly monitoring and diff-based alerting can be standardized with low marginal cost."
        ],
        risks=[
            "If source snapshots are not deduplicated by hash and locator, downstream evidence reuse will become noisy."
        ],
        next_steps=[
            "Resolve source list.",
            "Fetch and snapshot official materials.",
            "Persist source/source_snapshot.",
            "Emit extraction queue for evidence and metric layers."
        ],
        source_plan=[
            {"step": 1, "action": "resolve_official_scope"},
            {"step": 2, "action": "fetch_and_snapshot"},
            {"step": 3, "action": "queue_evidence_extraction"}
        ],
        db_write_plan=[
            "source",
            "source_snapshot",
            "evidence_item",
            "metric_observation"
        ],
        artifact_plan=[
            {"artifact_type": "excel", "template_code": "evidence_matrix_v1"}
        ]
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
