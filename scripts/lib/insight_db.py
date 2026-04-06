#!/usr/bin/env python3
import json
import hashlib
import re
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "config" / "insight_storage.json"
SECRETS_PATH = Path("/home/admin/.openclaw/secrets.json")

def utc_now():
    return datetime.now(timezone.utc)

def slugify(text: str, default: str = "item") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower())
    s = s.strip("-")
    return s or default

def sha1_text(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()

def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

def root_domain(url: str) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.strip().lower()
    return host or None

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def resolve_db_cfg() -> dict:
    raw = load_json(CFG_PATH)
    db = (
        raw.get("db")
        or raw.get("postgres")
        or raw.get("database")
        or ((raw.get("storage") or {}).get("db"))
        or ((raw.get("storage") or {}).get("postgres"))
        or ((raw.get("storage") or {}).get("database"))
        or {}
    )
    db = dict(db)

    if not db.get("password") and SECRETS_PATH.exists():
        secrets = load_json(SECRETS_PATH)
        pw = ((((secrets.get("postgres") or {}).get("oris_insight")) or {}).get("password"))
        if pw:
            db["password"] = pw

    return db

def db_connect():
    db = resolve_db_cfg()
    try:
        import psycopg2
        return psycopg2.connect(
            host=db["host"],
            port=db["port"],
            dbname=db["dbname"],
            user=db["user"],
            password=db.get("password", ""),
        )
    except ModuleNotFoundError:
        import psycopg
        return psycopg.connect(
            host=db["host"],
            port=db["port"],
            dbname=db["dbname"],
            user=db["user"],
            password=db.get("password", ""),
        )

def set_search_path(cur):
    cur.execute("SET search_path TO insight,public;")

def table_columns(cur, table_name: str) -> set[str]:
    set_search_path(cur)
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='insight' AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return {r[0] for r in cur.fetchall()}

def build_insert_sql(table_name: str, data: dict, returning: str = "id"):
    keys = list(data.keys())
    placeholders = []
    values = []
    for k in keys:
        if k.endswith("_json"):
            placeholders.append("%s::jsonb")
            values.append(json.dumps(data[k], ensure_ascii=False))
        else:
            placeholders.append("%s")
            values.append(data[k])
    sql = f"INSERT INTO {table_name}(" + ", ".join(keys) + ") VALUES (" + ", ".join(placeholders) + f") RETURNING {returning}"
    return sql, values

def maybe_select_company(cur, company_name: str, domain: str | None):
    cols = table_columns(cur, "company")
    set_search_path(cur)
    if domain and "domain" in cols:
        cur.execute("SELECT id FROM company WHERE domain=%s ORDER BY id DESC LIMIT 1", (domain,))
        row = cur.fetchone()
        if row:
            return row[0]
    if "company_name" in cols:
        cur.execute("SELECT id FROM company WHERE company_name=%s ORDER BY id DESC LIMIT 1", (company_name,))
        row = cur.fetchone()
        if row:
            return row[0]
    return None

def ensure_company(cur, company_name: str, domain: str | None = None, region: str | None = None):
    cols = table_columns(cur, "company")
    existing_id = maybe_select_company(cur, company_name, domain)
    if existing_id:
        return existing_id, "existing"

    code_base = slugify(domain or company_name, "company")
    company_code = f"{code_base}-{sha1_text(domain or company_name)[:8]}"

    payload = {}
    if "company_code" in cols:
        payload["company_code"] = company_code
    if "company_name" in cols:
        payload["company_name"] = company_name
    if "domain" in cols:
        payload["domain"] = domain
    if "region" in cols:
        payload["region"] = region
    if "status" in cols:
        payload["status"] = "active"
    if "is_target" in cols:
        payload["is_target"] = True
    if "is_competitor" in cols:
        payload["is_competitor"] = False

    set_search_path(cur)
    sql, values = build_insert_sql("company", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0], "inserted"

def maybe_select_source(cur, source_name: str, source_type: str | None, root_dom: str | None):
    cols = table_columns(cur, "source")
    set_search_path(cur)
    if all(x in cols for x in ["source_name", "source_type", "root_domain"]) and source_type is not None:
        cur.execute(
            "SELECT id FROM source WHERE source_name=%s AND source_type=%s AND COALESCE(root_domain,'')=COALESCE(%s,'') ORDER BY id DESC LIMIT 1",
            (source_name, source_type, root_dom),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    if "source_name" in cols:
        cur.execute("SELECT id FROM source WHERE source_name=%s ORDER BY id DESC LIMIT 1", (source_name,))
        row = cur.fetchone()
        if row:
            return row[0]
    return None

def ensure_source(cur, source_name: str, source_type: str, source_url: str | None = None, publisher: str | None = None, official_flag: bool = True):
    cols = table_columns(cur, "source")
    root_dom = root_domain(source_url)
    existing_id = maybe_select_source(cur, source_name, source_type, root_dom)
    if existing_id:
        return existing_id, "existing"

    code_base = slugify(f"{source_type}-{source_name}", "source")
    source_code = f"{code_base}-{sha1_text((source_url or source_name or source_type))[:8]}"

    payload = {}
    if "source_code" in cols:
        payload["source_code"] = source_code
    if "source_name" in cols:
        payload["source_name"] = source_name
    if "source_type" in cols:
        payload["source_type"] = source_type
    if "source_priority" in cols:
        payload["source_priority"] = 100 if official_flag else 50
    if "root_domain" in cols:
        payload["root_domain"] = root_dom
    if "publisher" in cols:
        payload["publisher"] = publisher or root_dom
    if "official_flag" in cols:
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
    cols = table_columns(cur, "source_snapshot")
    payload = {}
    if "source_id" in cols:
        payload["source_id"] = source_id
    if "company_id" in cols:
        payload["company_id"] = company_id
    if "snapshot_type" in cols:
        payload["snapshot_type"] = snapshot_type
    if "snapshot_title" in cols:
        payload["snapshot_title"] = snapshot_title
    if "snapshot_url" in cols:
        payload["snapshot_url"] = snapshot_url
    if "snapshot_time" in cols:
        payload["snapshot_time"] = metadata_json.get("snapshot_time")
    if "fetch_time" in cols:
        payload["fetch_time"] = metadata_json.get("fetch_time")
    if "content_hash" in cols:
        payload["content_hash"] = content_hash
    if "raw_storage_path" in cols:
        payload["raw_storage_path"] = raw_storage_path
    if "parsed_text_storage_path" in cols:
        payload["parsed_text_storage_path"] = parsed_text_storage_path
    if "metadata_json" in cols:
        payload["metadata_json"] = metadata_json

    set_search_path(cur)
    sql, values = build_insert_sql("source_snapshot", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0]

def insert_analysis_run(cur, request_id: str, analysis_type: str, target_company_id: int | None, request_payload: dict, run_note: str | None = None):
    cols = table_columns(cur, "analysis_run")
    run_code = f"{slugify(analysis_type, 'analysis')}-{sha1_text(request_id)[:8]}"
    payload = {}

    if "run_code" in cols:
        payload["run_code"] = run_code
    if "request_id" in cols:
        payload["request_id"] = request_id
    if "analysis_type" in cols:
        payload["analysis_type"] = analysis_type
    if "target_company_id" in cols:
        payload["target_company_id"] = target_company_id
    if "status" in cols:
        payload["status"] = "completed"
    if "input_json" in cols:
        payload["input_json"] = request_payload
    if "request_json" in cols:
        payload["request_json"] = request_payload
    if "metadata_json" in cols:
        payload["metadata_json"] = {"note": run_note or "official source ingest bootstrap write"}
    if "started_at" in cols:
        payload["started_at"] = utc_now()
    if "completed_at" in cols:
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
    cols = table_columns(cur, "evidence_item")
    payload = {}
    if "source_snapshot_id" in cols:
        payload["source_snapshot_id"] = source_snapshot_id
    if "company_id" in cols:
        payload["company_id"] = company_id
    if "evidence_type" in cols:
        payload["evidence_type"] = evidence_type
    if "evidence_title" in cols:
        payload["evidence_title"] = evidence_title
    if "evidence_text" in cols:
        payload["evidence_text"] = evidence_text
    if "evidence_number" in cols:
        payload["evidence_number"] = evidence_number
    if "evidence_unit" in cols:
        payload["evidence_unit"] = evidence_unit
    if "evidence_date" in cols:
        payload["evidence_date"] = evidence_date
    if "confidence_score" in cols:
        payload["confidence_score"] = confidence_score
    if "locator_json" in cols:
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
    cols = table_columns(cur, "metric_observation")
    payload = {}
    if "company_id" in cols:
        payload["company_id"] = company_id
    if "metric_code" in cols:
        payload["metric_code"] = metric_code
    if "metric_name" in cols:
        payload["metric_name"] = metric_name
    if "metric_value" in cols:
        payload["metric_value"] = metric_value
    if "metric_unit" in cols:
        payload["metric_unit"] = metric_unit
    if "period_type" in cols:
        payload["period_type"] = period_type
    if "observation_date" in cols:
        payload["observation_date"] = observation_date
    if "source_snapshot_id" in cols:
        payload["source_snapshot_id"] = source_snapshot_id
    if "evidence_item_id" in cols:
        payload["evidence_item_id"] = evidence_item_id
    if "normalization_rule" in cols:
        payload["normalization_rule"] = normalization_rule

    set_search_path(cur)
    sql, values = build_insert_sql("metric_observation", payload)
    cur.execute(sql, values)
    return cur.fetchone()[0]
