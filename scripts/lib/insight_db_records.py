from __future__ import annotations

from datetime import date

from scripts.lib.insight_db_schema import set_search_path, table_columns
from scripts.lib.insight_db_utils import build_insert_sql, sha1_text, slugify, utc_now


def insert_analysis_run(
    cur,
    request_id: str,
    analysis_type: str,
    target_company_id: int | None,
    request_payload: dict,
    run_note: str | None = None,
):
    columns = table_columns(cur, "analysis_run")
    run_code = f"{slugify(analysis_type, 'analysis')}-{sha1_text(request_id)[:8]}"
    payload = {}
    if "run_code" in columns:
        payload["run_code"] = run_code
    if "request_id" in columns:
        payload["request_id"] = request_id
    if "analysis_type" in columns:
        payload["analysis_type"] = analysis_type
    if "target_company_id" in columns:
        payload["target_company_id"] = target_company_id
    if "status" in columns:
        payload["status"] = "completed"
    if "input_json" in columns:
        payload["input_json"] = request_payload
    if "request_json" in columns:
        payload["request_json"] = request_payload
    if "metadata_json" in columns:
        payload["metadata_json"] = {
            "note": run_note or "official source ingest bootstrap write"
        }
    if "started_at" in columns:
        payload["started_at"] = utc_now()
    if "completed_at" in columns:
        payload["completed_at"] = utc_now()
    set_search_path(cur)
    sql, values = build_insert_sql("analysis_run", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0], run_code


def insert_evidence_item(
    cur,
    source_snapshot_id: int,
    company_id: int,
    evidence_type: str,
    evidence_title: str,
    evidence_text: str,
    evidence_number=None,
    evidence_unit: str | None = None,
    evidence_date: date | None = None,
    confidence_score: float | None = None,
    locator_json: dict | None = None,
):
    columns = table_columns(cur, "evidence_item")
    payload = {}
    if "source_snapshot_id" in columns:
        payload["source_snapshot_id"] = source_snapshot_id
    if "company_id" in columns:
        payload["company_id"] = company_id
    if "evidence_type" in columns:
        payload["evidence_type"] = evidence_type
    if "evidence_title" in columns:
        payload["evidence_title"] = evidence_title
    if "evidence_text" in columns:
        payload["evidence_text"] = evidence_text
    if "evidence_number" in columns:
        payload["evidence_number"] = evidence_number
    if "evidence_unit" in columns:
        payload["evidence_unit"] = evidence_unit
    if "evidence_date" in columns:
        payload["evidence_date"] = evidence_date
    if "confidence_score" in columns:
        payload["confidence_score"] = confidence_score
    if "locator_json" in columns:
        payload["locator_json"] = locator_json or {}
    set_search_path(cur)
    sql, values = build_insert_sql("evidence_item", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0]


def insert_metric_observation(
    cur,
    company_id: int,
    metric_code: str,
    metric_name: str,
    metric_value,
    metric_unit: str,
    period_type: str,
    observation_date,
    source_snapshot_id: int | None = None,
    evidence_item_id: int | None = None,
    normalization_rule: str | None = None,
):
    columns = table_columns(cur, "metric_observation")
    payload = {}
    if "company_id" in columns:
        payload["company_id"] = company_id
    if "metric_code" in columns:
        payload["metric_code"] = metric_code
    if "metric_name" in columns:
        payload["metric_name"] = metric_name
    if "metric_value" in columns:
        payload["metric_value"] = metric_value
    if "metric_unit" in columns:
        payload["metric_unit"] = metric_unit
    if "period_type" in columns:
        payload["period_type"] = period_type
    if "observation_date" in columns:
        payload["observation_date"] = observation_date
    if "source_snapshot_id" in columns:
        payload["source_snapshot_id"] = source_snapshot_id
    if "evidence_item_id" in columns:
        payload["evidence_item_id"] = evidence_item_id
    if "normalization_rule" in columns:
        payload["normalization_rule"] = normalization_rule
    set_search_path(cur)
    sql, values = build_insert_sql("metric_observation", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0]
