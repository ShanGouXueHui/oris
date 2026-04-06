#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_db import db_connect, set_search_path
from lib.insight_skill_runtime import build_standard_output, load_request

SKILL_NAME = "company_profile_skill"

DEFAULT_REQUEST = {
    "company_name": "Canonical",
    "domain": "canonical.com",
    "region": "global"
}

def json_safe(value):
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value

def fetch_one(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))

def fetch_all(cur, sql, params=()):
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None)
    args = ap.parse_args()

    request = load_request(args.input_file, args.input_json, DEFAULT_REQUEST)
    company_name = request.get("company_name") or request.get("entity") or "unknown"
    domain = request.get("domain")
    region = request.get("region")

    conn = db_connect()
    try:
        with conn:
            with conn.cursor() as cur:
                set_search_path(cur)

                company = None
                if domain:
                    company = fetch_one(
                        cur,
                        """
                        SELECT id, company_code, company_name, domain, region, status
                        FROM company
                        WHERE domain=%s
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (domain,),
                    )

                if not company:
                    company = fetch_one(
                        cur,
                        """
                        SELECT id, company_code, company_name, domain, region, status
                        FROM company
                        WHERE company_name=%s
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (company_name,),
                    )

                if not company:
                    out = build_standard_output(
                        skill_name=SKILL_NAME,
                        request=request,
                        conclusion="company_profile_skill did not find a persisted company profile in insight DB yet.",
                        core_data=[
                            {"field": "company_name", "value": company_name},
                            {"field": "domain", "value": domain},
                            {"field": "db_company_found", "value": False},
                        ],
                        sources=[],
                        facts=[
                            "No matching company row was found in insight.company for the provided company_name/domain."
                        ],
                        inferences=[
                            "official_source_ingest_skill should run first to persist company/source/source_snapshot/evidence/metric records."
                        ],
                        hypotheses=[],
                        risks=[
                            "Without a persisted company row, downstream profile/report generation will drift back to request-only behavior."
                        ],
                        next_steps=[
                            "Run official_source_ingest_skill first.",
                            "Re-run company_profile_skill after source/evidence/metric rows exist."
                        ],
                        source_plan=[],
                        db_write_plan=[],
                        artifact_plan=[],
                    )
                    print(json.dumps(json_safe(out), ensure_ascii=False, indent=2))
                    return

                company_id = company["id"]

                analysis_runs = fetch_all(
                    cur,
                    """
                    SELECT id, run_code, request_id, analysis_type, target_company_id
                    FROM analysis_run
                    WHERE target_company_id=%s
                    ORDER BY id DESC
                    LIMIT 10
                    """,
                    (company_id,),
                )

                snapshots = fetch_all(
                    cur,
                    """
                    SELECT
                        ss.id,
                        ss.source_id,
                        ss.company_id,
                        ss.snapshot_type,
                        ss.snapshot_title,
                        ss.snapshot_url,
                        ss.raw_storage_path,
                        ss.parsed_text_storage_path,
                        ss.created_at,
                        s.source_name,
                        s.source_type,
                        s.root_domain,
                        s.official_flag
                    FROM source_snapshot ss
                    LEFT JOIN source s ON s.id = ss.source_id
                    WHERE ss.company_id=%s
                    ORDER BY ss.id DESC
                    LIMIT 10
                    """,
                    (company_id,),
                )

                evidence_rows = fetch_all(
                    cur,
                    """
                    SELECT
                        id,
                        source_snapshot_id,
                        company_id,
                        evidence_type,
                        evidence_title,
                        evidence_text,
                        evidence_number,
                        evidence_unit,
                        evidence_date,
                        confidence_score
                    FROM evidence_item
                    WHERE company_id=%s
                    ORDER BY id DESC
                    LIMIT 10
                    """,
                    (company_id,),
                )

                metric_rows = fetch_all(
                    cur,
                    """
                    SELECT
                        id,
                        company_id,
                        metric_code,
                        metric_name,
                        metric_value,
                        metric_unit,
                        period_type,
                        observation_date,
                        source_snapshot_id,
                        evidence_item_id
                    FROM metric_observation
                    WHERE company_id=%s
                    ORDER BY id DESC
                    LIMIT 10
                    """,
                    (company_id,),
                )

                facts = [
                    f"Company row found in insight.company with company_id={company_id}.",
                    f"Recent analysis_run count in profile view: {len(analysis_runs)}.",
                    f"Recent source_snapshot count in profile view: {len(snapshots)}.",
                    f"Recent evidence_item count in profile view: {len(evidence_rows)}.",
                    f"Recent metric_observation count in profile view: {len(metric_rows)}."
                ]

                inferences = []
                if snapshots:
                    inferences.append("The company profile can now be grounded on persisted snapshots instead of request-only payload.")
                if evidence_rows and metric_rows:
                    inferences.append("The minimum DB-backed evidence chain exists and can support downstream report assembly.")
                if not evidence_rows or not metric_rows:
                    inferences.append("The DB-backed profile exists but evidence/metric density is still thin.")

                risks = []
                if not snapshots:
                    risks.append("No source snapshots found; profile will remain structurally incomplete.")
                if not evidence_rows:
                    risks.append("Evidence rows are missing or too sparse; conclusions may not be auditable enough.")
                if not metric_rows:
                    risks.append("Metric rows are missing or too sparse; comparison and trend analysis remain weak.")
                if evidence_rows and metric_rows:
                    risks.append("Current evidence and metrics are still bootstrap-level placeholders until live fetch/extraction is added.")

                sources = []
                for row in snapshots:
                    sources.append({
                        "source_type": row.get("source_type") or row.get("snapshot_type"),
                        "source_name": row.get("source_name"),
                        "url": row.get("snapshot_url"),
                        "official_flag": row.get("official_flag"),
                        "source_snapshot_id": row.get("id"),
                    })

                core_data = [
                    {"field": "company_id", "value": company.get("id")},
                    {"field": "company_code", "value": company.get("company_code")},
                    {"field": "company_name", "value": company.get("company_name")},
                    {"field": "domain", "value": company.get("domain")},
                    {"field": "region", "value": company.get("region") or region},
                    {"field": "analysis_run_count_recent", "value": len(analysis_runs)},
                    {"field": "source_snapshot_count_recent", "value": len(snapshots)},
                    {"field": "evidence_item_count_recent", "value": len(evidence_rows)},
                    {"field": "metric_observation_count_recent", "value": len(metric_rows)},
                ]

                out = build_standard_output(
                    skill_name=SKILL_NAME,
                    request=request,
                    conclusion="company_profile_skill DB-backed profile ready; it now reads persisted company/source/evidence/metric records from insight DB.",
                    core_data=core_data,
                    sources=sources,
                    facts=facts,
                    inferences=inferences,
                    hypotheses=[
                        "As official_source_ingest_skill accumulates more live snapshots and extracted evidence, this company profile can become the stable upstream layer for competitor research and report build."
                    ],
                    risks=risks,
                    next_steps=[
                        "Increase official source coverage for the target company.",
                        "Replace bootstrap evidence with extracted body-level evidence.",
                        "Let report_build_skill consume analysis_run/evidence/metric rows."
                    ],
                    source_plan=snapshots,
                    db_write_plan=[],
                    artifact_plan=[
                        {"artifact_type": "word", "template_code": "enterprise_report_v1"},
                        {"artifact_type": "excel", "template_code": "evidence_matrix_v1"},
                        {"artifact_type": "ppt", "template_code": "executive_briefing_v1"},
                    ],
                )

                out["db_backed_profile"] = {
                    "company": company,
                    "analysis_runs": analysis_runs,
                    "recent_snapshots": snapshots,
                    "recent_evidence_items": evidence_rows,
                    "recent_metric_observations": metric_rows,
                }

                print(json.dumps(json_safe(out), ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
