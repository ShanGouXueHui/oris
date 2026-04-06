#!/usr/bin/env python3
import argparse
import json
import sys
import uuid
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_db import (
    db_connect,
    ensure_company,
    ensure_source,
    insert_source_snapshot,
    insert_analysis_run,
    insert_evidence_item,
    insert_metric_observation,
    sha256_text,
)
from lib.insight_skill_runtime import build_standard_output, load_request

SKILL_NAME = "official_source_ingest_skill"
OUTPUT_ROOT = ROOT / "outputs" / "insight_ingest"

DEFAULT_REQUEST = {
    "entity": "Canonical",
    "domain": "canonical.com",
    "region": "global",
    "time_range": "latest",
    "sources": [
        {
            "source_name": "Canonical Official Website",
            "source_type": "official_website",
            "url": "https://canonical.com/",
            "title": "Canonical Homepage",
            "publisher": "Canonical",
            "official_flag": True
        }
    ]
}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def slugify(text: str, default: str = "item") -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower())
    s = s.strip("-")
    return s or default

def ensure_sources(request: dict):
    explicit = request.get("sources")
    if isinstance(explicit, list) and explicit:
        return explicit

    entity = request.get("entity") or "unknown"
    domain = request.get("domain")
    scope = request.get("source_scope") or ["official_website"]
    out = []
    for item in scope:
        item = str(item)
        url = None
        title = f"{entity} {item}"
        if item == "official_website" and domain:
            url = f"https://{domain}/"
            title = f"{entity} homepage"
        elif item == "investor_relations" and domain:
            url = f"https://{domain}/investor-relations"
            title = f"{entity} investor relations"
        elif item == "annual_report" and domain:
            url = f"https://{domain}/annual-report"
            title = f"{entity} annual report"
        out.append({
            "source_name": f"{entity} {item}",
            "source_type": item,
            "url": url,
            "title": title,
            "publisher": entity,
            "official_flag": True
        })
    return out

def write_snapshot_files(entity: str, source_item: dict, index_num: int):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    entity_slug = slugify(entity, "entity")
    base = OUTPUT_ROOT / entity_slug / ts
    base.mkdir(parents=True, exist_ok=True)

    raw_payload = {
        "entity": entity,
        "source": source_item,
        "captured_at": utc_now(),
        "note": "bootstrap write without live fetch body"
    }
    parsed_text = "\n".join([
        f"title: {source_item.get('title') or source_item.get('source_name')}",
        f"url: {source_item.get('url') or ''}",
        f"source_type: {source_item.get('source_type') or ''}",
        f"publisher: {source_item.get('publisher') or ''}",
        f"captured_at: {raw_payload['captured_at']}",
    ]).strip() + "\n"

    raw_path = base / f"source_{index_num:02d}_raw.json"
    parsed_path = base / f"source_{index_num:02d}_parsed.txt"

    raw_text = json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n"
    raw_path.write_text(raw_text, encoding="utf-8")
    parsed_path.write_text(parsed_text, encoding="utf-8")

    return {
        "raw_storage_path": str(raw_path.relative_to(ROOT)),
        "parsed_text_storage_path": str(parsed_path.relative_to(ROOT)),
        "content_hash": sha256_text(raw_text),
        "snapshot_time": raw_payload["captured_at"],
        "fetch_time": raw_payload["captured_at"],
        "parsed_text": parsed_text,
    }

def build_bootstrap_evidence_text(entity: str, src: dict, file_info: dict):
    lines = [
        f"entity: {entity}",
        f"source_name: {src.get('source_name') or ''}",
        f"source_type: {src.get('source_type') or ''}",
        f"title: {src.get('title') or ''}",
        f"url: {src.get('url') or ''}",
        f"publisher: {src.get('publisher') or ''}",
        f"snapshot_time: {file_info.get('snapshot_time') or ''}",
        f"raw_storage_path: {file_info.get('raw_storage_path') or ''}",
        f"parsed_text_storage_path: {file_info.get('parsed_text_storage_path') or ''}",
    ]
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    request = load_request(args.input_file, args.input_json, DEFAULT_REQUEST)
    request_id = str(uuid.uuid4())
    entity = request.get("entity") or request.get("company_name") or "unknown"
    domain = request.get("domain")
    region = request.get("region")
    sources = ensure_sources(request)

    planned = []
    for i, src in enumerate(sources, start=1):
        file_info = write_snapshot_files(entity, src, i)
        planned.append({
            "source_name": src.get("source_name"),
            "source_type": src.get("source_type"),
            "url": src.get("url"),
            **file_info
        })

    if args.dry_run:
        out = build_standard_output(
            skill_name=SKILL_NAME,
            request=request,
            conclusion="official_source_ingest_skill dry-run ready; company/source/source_snapshot/analysis_run/evidence_item/metric_observation write plan resolved.",
            core_data=[
                {"field": "entity", "value": entity},
                {"field": "domain", "value": domain},
                {"field": "planned_snapshot_count", "value": len(planned)},
                {"field": "planned_evidence_count", "value": len(planned)},
                {"field": "planned_metric_count", "value": len(planned)}
            ],
            sources=[{"source_type": x.get("source_type"), "required": True} for x in planned],
            facts=[
                "This dry-run already materializes local raw/parsed snapshot files.",
                "DB write target for this step is company/source/source_snapshot/analysis_run/evidence_item/metric_observation."
            ],
            inferences=[
                "Once this write path is stable, company_profile_skill can consume durable snapshot/evidence/metric ids instead of temporary payloads."
            ],
            hypotheses=[],
            risks=[
                "This step still uses bootstrap metadata evidence, not live fetched page body."
            ],
            next_steps=[
                "Run without --dry-run to persist into insight schema.",
                "Add live fetch/body parsing.",
                "Replace bootstrap evidence with extracted evidence."
            ],
            source_plan=planned,
            db_write_plan=["company", "source", "source_snapshot", "analysis_run", "evidence_item", "metric_observation"],
            artifact_plan=[]
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    conn = db_connect()
    results = []
    try:
        with conn:
            with conn.cursor() as cur:
                company_id, company_action = ensure_company(cur, entity, domain=domain, region=region)
                analysis_run_id, run_code = insert_analysis_run(
                    cur,
                    request_id=request_id,
                    analysis_type="official_source_ingest",
                    target_company_id=company_id,
                    request_payload=request,
                    run_note="bootstrap source ingest with analysis/evidence/metric writes",
                )

                for i, src in enumerate(sources, start=1):
                    file_info = planned[i - 1]
                    source_id, source_action = ensure_source(
                        cur,
                        source_name=src.get("source_name") or f"{entity} source {i}",
                        source_type=src.get("source_type") or "official_website",
                        source_url=src.get("url"),
                        publisher=src.get("publisher"),
                        official_flag=bool(src.get("official_flag", True)),
                    )
                    snapshot_id = insert_source_snapshot(
                        cur,
                        source_id=source_id,
                        company_id=company_id,
                        snapshot_type=src.get("source_type") or "official_website",
                        snapshot_title=src.get("title") or src.get("source_name") or f"{entity} source {i}",
                        snapshot_url=src.get("url"),
                        raw_storage_path=file_info["raw_storage_path"],
                        parsed_text_storage_path=file_info["parsed_text_storage_path"],
                        content_hash=file_info["content_hash"],
                        metadata_json={
                            "entity": entity,
                            "request_time_range": request.get("time_range"),
                            "snapshot_time": file_info["snapshot_time"],
                            "fetch_time": file_info["fetch_time"],
                            "source_name": src.get("source_name"),
                            "source_type": src.get("source_type"),
                            "url": src.get("url"),
                            "runner": SKILL_NAME,
                            "analysis_run_id": analysis_run_id,
                            "request_id": request_id
                        },
                    )

                    evidence_text = build_bootstrap_evidence_text(entity, src, file_info)
                    evidence_id = insert_evidence_item(
                        cur,
                        source_snapshot_id=snapshot_id,
                        company_id=company_id,
                        evidence_type="source_capture",
                        evidence_title=src.get("title") or src.get("source_name") or f"{entity} source {i}",
                        evidence_text=evidence_text,
                        evidence_number=None,
                        evidence_unit=None,
                        evidence_date=date.today(),
                        confidence_score=0.6,
                        locator_json={
                            "url": src.get("url"),
                            "raw_storage_path": file_info["raw_storage_path"],
                            "parsed_text_storage_path": file_info["parsed_text_storage_path"],
                            "analysis_run_id": analysis_run_id,
                            "request_id": request_id
                        },
                    )

                    metric_id = insert_metric_observation(
                        cur,
                        company_id=company_id,
                        metric_code="official_source_snapshot_count",
                        metric_name="Official Source Snapshot Count",
                        metric_value=1,
                        metric_unit="count",
                        period_type="point_in_time",
                        observation_date=date.today(),
                        source_snapshot_id=snapshot_id,
                        evidence_item_id=evidence_id,
                        normalization_rule="1 row per ingested official source snapshot",
                    )

                    results.append({
                        "analysis_run_id": analysis_run_id,
                        "run_code": run_code,
                        "company_id": company_id,
                        "company_action": company_action,
                        "source_id": source_id,
                        "source_action": source_action,
                        "snapshot_id": snapshot_id,
                        "evidence_id": evidence_id,
                        "metric_id": metric_id,
                        "source_name": src.get("source_name"),
                        "source_type": src.get("source_type"),
                        "url": src.get("url"),
                        "raw_storage_path": file_info["raw_storage_path"],
                        "parsed_text_storage_path": file_info["parsed_text_storage_path"],
                    })

        out = build_standard_output(
            skill_name=SKILL_NAME,
            request=request,
            conclusion="official_source_ingest_skill real-write succeeded; company/source/source_snapshot/analysis_run/evidence_item/metric_observation persisted into insight schema.",
            core_data=[
                {"field": "entity", "value": entity},
                {"field": "company_id", "value": results[0]["company_id"] if results else None},
                {"field": "analysis_run_id", "value": results[0]["analysis_run_id"] if results else None},
                {"field": "written_snapshot_count", "value": len(results)},
                {"field": "written_evidence_count", "value": len(results)},
                {"field": "written_metric_count", "value": len(results)}
            ],
            sources=[{"source_type": x.get("source_type"), "url": x.get("url")} for x in results],
            facts=[
                "Company record ensured in insight.company.",
                "Source records ensured in insight.source.",
                "Snapshot rows inserted into insight.source_snapshot.",
                "Analysis run row inserted into insight.analysis_run.",
                "Bootstrap evidence rows inserted into insight.evidence_item.",
                "Bootstrap metric rows inserted into insight.metric_observation."
            ],
            inferences=[
                "This creates the minimum durable chain needed for downstream company profile and report assembly."
            ],
            hypotheses=[],
            risks=[
                "Evidence and metric rows are still bootstrap-level placeholders until live fetch and extraction are integrated."
            ],
            next_steps=[
                "Attach live fetch body.",
                "Extract real evidence_item from parsed text.",
                "Derive domain metrics beyond snapshot count."
            ],
            source_plan=results,
            db_write_plan=["company", "source", "source_snapshot", "analysis_run", "evidence_item", "metric_observation"],
            artifact_plan=[]
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
