#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_db import (
    db_connect,
    ensure_company,
    ensure_source,
    insert_source_snapshot,
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
        "note": "scaffold real-write bootstrap without live fetch body"
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
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--input-json", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    request = load_request(args.input_file, args.input_json, DEFAULT_REQUEST)
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
            conclusion="official_source_ingest_skill dry-run ready; company/source/source_snapshot write plan resolved.",
            core_data=[
                {"field": "entity", "value": entity},
                {"field": "domain", "value": domain},
                {"field": "planned_snapshot_count", "value": len(planned)}
            ],
            sources=[{"source_type": x.get("source_type"), "required": True} for x in planned],
            facts=[
                "This dry-run already materializes local raw/parsed snapshot files.",
                "DB write target for this step is company/source/source_snapshot."
            ],
            inferences=[
                "Once this write path is stable, evidence_item and metric_observation can be layered on the same source_snapshot ids."
            ],
            hypotheses=[],
            risks=[
                "This step does not yet fetch live page body; downstream evidence extraction is still placeholder-level."
            ],
            next_steps=[
                "Run without --dry-run to persist into insight schema.",
                "Add real fetch/body parsing.",
                "Attach evidence and metric extraction."
            ],
            source_plan=planned,
            db_write_plan=["company", "source", "source_snapshot"],
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
                            "runner": SKILL_NAME
                        },
                    )
                    results.append({
                        "company_id": company_id,
                        "company_action": company_action,
                        "source_id": source_id,
                        "source_action": source_action,
                        "snapshot_id": snapshot_id,
                        "source_name": src.get("source_name"),
                        "source_type": src.get("source_type"),
                        "url": src.get("url"),
                        "raw_storage_path": file_info["raw_storage_path"],
                        "parsed_text_storage_path": file_info["parsed_text_storage_path"],
                    })
        out = build_standard_output(
            skill_name=SKILL_NAME,
            request=request,
            conclusion="official_source_ingest_skill real-write succeeded; company/source/source_snapshot persisted into insight schema.",
            core_data=[
                {"field": "entity", "value": entity},
                {"field": "company_id", "value": results[0]["company_id"] if results else None},
                {"field": "written_snapshot_count", "value": len(results)}
            ],
            sources=[{"source_type": x.get("source_type"), "url": x.get("url")} for x in results],
            facts=[
                "Company record ensured in insight.company.",
                "Source records ensured in insight.source.",
                "Snapshot rows inserted into insight.source_snapshot."
            ],
            inferences=[
                "This establishes the durable upstream ids needed for evidence_item and metric_observation."
            ],
            hypotheses=[],
            risks=[
                "Live page body fetch/parsing is not yet integrated; current raw snapshot is metadata bootstrap."
            ],
            next_steps=[
                "Attach live fetch body.",
                "Extract evidence_item from source_snapshot.",
                "Extract metric_observation from evidence_item."
            ],
            source_plan=results,
            db_write_plan=["company", "source", "source_snapshot"],
            artifact_plan=[]
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
