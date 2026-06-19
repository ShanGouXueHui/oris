#!/usr/bin/env python3
from __future__ import annotations

from scripts.lib.insight_db_config import db_connect, load_json, resolve_db_cfg
from scripts.lib.insight_db_records import (
    insert_analysis_run,
    insert_evidence_item,
    insert_metric_observation,
)
from scripts.lib.insight_db_schema import set_search_path, table_columns
from scripts.lib.insight_db_utils import (
    build_insert_sql,
    root_domain,
    sha1_text,
    sha256_text,
    slugify,
    utc_now,
)


def maybe_select_company(cur, company_name: str, domain: str | None):
    columns = table_columns(cur, "company")
    set_search_path(cur)
    if domain and "domain" in columns:
        cur.execute(
            "SELECT id FROM company WHERE domain=%s ORDER BY id DESC LIMIT 1",
            (domain,),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    if "company_name" in columns:
        cur.execute(
            "SELECT id FROM company WHERE company_name=%s ORDER BY id DESC LIMIT 1",
            (company_name,),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    return None


def ensure_company(
    cur,
    company_name: str,
    domain: str | None = None,
    region: str | None = None,
):
    columns = table_columns(cur, "company")
    existing_id = maybe_select_company(cur, company_name, domain)
    if existing_id:
        return existing_id, "existing"

    code_base = slugify(domain or company_name, "company")
    company_code = f"{code_base}-{sha1_text(domain or company_name)[:8]}"
    payload = {}
    if "company_code" in columns:
        payload["company_code"] = company_code
    if "company_name" in columns:
        payload["company_name"] = company_name
    if "domain" in columns:
        payload["domain"] = domain
    if "region" in columns:
        payload["region"] = region
    if "status" in columns:
        payload["status"] = "active"
    if "is_target" in columns:
        payload["is_target"] = True
    if "is_competitor" in columns:
        payload["is_competitor"] = False

    set_search_path(cur)
    sql, values = build_insert_sql("company", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0], "inserted"


def maybe_select_source(
    cur,
    source_name: str,
    source_type: str | None,
    root_dom: str | None,
):
    columns = table_columns(cur, "source")
    set_search_path(cur)
    required = ["source_name", "source_type", "root_domain"]
    if all(name in columns for name in required) and source_type is not None:
        cur.execute(
            "SELECT id FROM source WHERE source_name=%s AND source_type=%s "
            "AND COALESCE(root_domain,'')=COALESCE(%s,'') "
            "ORDER BY id DESC LIMIT 1",
            (source_name, source_type, root_dom),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    if "source_name" in columns:
        cur.execute(
            "SELECT id FROM source WHERE source_name=%s ORDER BY id DESC LIMIT 1",
            (source_name,),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    return None


def ensure_source(
    cur,
    source_name: str,
    source_type: str,
    source_url: str | None = None,
    publisher: str | None = None,
    official_flag: bool = True,
):
    columns = table_columns(cur, "source")
    root_dom = root_domain(source_url)
    existing_id = maybe_select_source(cur, source_name, source_type, root_dom)
    if existing_id:
        return existing_id, "existing"

    code_base = slugify(f"{source_type}-{source_name}", "source")
    source_code = f"{code_base}-{sha1_text(source_url or source_name or source_type)[:8]}"
    payload = {}
    if "source_code" in columns:
        payload["source_code"] = source_code
    if "source_name" in columns:
        payload["source_name"] = source_name
    if "source_type" in columns:
        payload["source_type"] = source_type
    if "source_priority" in columns:
        payload["source_priority"] = 100 if official_flag else 50
    if "root_domain" in columns:
        payload["root_domain"] = root_dom
    if "publisher" in columns:
        payload["publisher"] = publisher or root_dom
    if "official_flag" in columns:
        payload["official_flag"] = bool(official_flag)

    set_search_path(cur)
    sql, values = build_insert_sql("source", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0], "inserted"


def insert_source_snapshot(
    cur,
    source_id: int,
    company_id: int,
    snapshot_type: str,
    snapshot_title: str,
    snapshot_url: str | None,
    raw_storage_path: str | None,
    parsed_text_storage_path: str | None,
    content_hash: str | None,
    metadata_json: dict,
):
    columns = table_columns(cur, "source_snapshot")
    payload = {}
    if "source_id" in columns:
        payload["source_id"] = source_id
    if "company_id" in columns:
        payload["company_id"] = company_id
    if "snapshot_type" in columns:
        payload["snapshot_type"] = snapshot_type
    if "snapshot_title" in columns:
        payload["snapshot_title"] = snapshot_title
    if "snapshot_url" in columns:
        payload["snapshot_url"] = snapshot_url
    if "snapshot_time" in columns:
        payload["snapshot_time"] = metadata_json.get("snapshot_time")
    if "fetch_time" in columns:
        payload["fetch_time"] = metadata_json.get("fetch_time")
    if "content_hash" in columns:
        payload["content_hash"] = content_hash
    if "raw_storage_path" in columns:
        payload["raw_storage_path"] = raw_storage_path
    if "parsed_text_storage_path" in columns:
        payload["parsed_text_storage_path"] = parsed_text_storage_path
    if "metadata_json" in columns:
        payload["metadata_json"] = metadata_json

    set_search_path(cur)
    sql, values = build_insert_sql("source_snapshot", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0]
