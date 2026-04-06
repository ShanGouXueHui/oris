#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import uuid
import urllib.request
import urllib.error
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[2]
SKILL_RUNTIME_PATH = ROOT / "config" / "insight_skill_runtime.json"
INSIGHT_STORAGE_PATH = ROOT / "config" / "insight_storage.json"
DEFAULT_TIMEOUT = 30


def utc_now():
    return datetime.now(timezone.utc)


def utc_now_iso():
    return utc_now().isoformat()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_slug(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return s or "unknown"


def text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def to_jsonable(value):
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def skill_cfg():
    data = load_json(SKILL_RUNTIME_PATH)
    return (data.get("skills") or {}).get("official_source_ingest_skill") or {}


def load_db_cfg():
    raw = load_json(INSIGHT_STORAGE_PATH)
    db = (
        raw.get("db")
        or raw.get("postgres")
        or raw.get("database")
        or (raw.get("storage") or {}).get("db")
        or (raw.get("storage") or {}).get("postgres")
        or (raw.get("storage") or {}).get("database")
    )
    if not isinstance(db, dict):
        raise RuntimeError("db config missing in config/insight_storage.json")
    return {
        "host": db["host"],
        "port": db["port"],
        "dbname": db["dbname"],
        "user": db["user"],
        "password": db.get("password", ""),
    }


def db_connect():
    return psycopg2.connect(**load_db_cfg())


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_ignored = 0
        self.text_parts = []
        self.title_parts = []
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in {"script", "style", "noscript"}:
            self.in_ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.in_ignored > 0:
            self.in_ignored -= 1
        self.current_tag = None

    def handle_data(self, data):
        if self.in_ignored > 0:
            return
        text = normalize_text(data)
        if not text:
            return
        if self.current_tag == "title":
            self.title_parts.append(text)
        self.text_parts.append(text)

    def result(self):
        title = " ".join(self.title_parts).strip()
        body = "\n".join(self.text_parts).strip()
        body = re.sub(r"\n{2,}", "\n", body)
        return title, body


def decode_bytes(raw: bytes, content_type: str) -> str:
    charset = None
    m = re.search(r"charset=([A-Za-z0-9_\-]+)", content_type or "", re.IGNORECASE)
    if m:
        charset = m.group(1).strip()
    for enc in [charset, "utf-8", "utf-16", "latin-1"]:
        if not enc:
            continue
        try:
            return raw.decode(enc, errors="ignore")
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ORIS-InsightIngest/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            final_url = resp.geturl()
            status_code = getattr(resp, "status", 200)
            text = decode_bytes(raw, content_type)

            if "html" in (content_type or "").lower() or "<html" in text.lower():
                parser = HTMLTextExtractor()
                parser.feed(text)
                title, body = parser.result()
            else:
                title = ""
                body = text

            return {
                "ok": True,
                "status_code": status_code,
                "content_type": content_type,
                "final_url": final_url,
                "raw_text": text,
                "title": title,
                "body_text": body,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "status_code": e.code,
            "content_type": "",
            "final_url": url,
            "raw_text": "",
            "title": "",
            "body_text": "",
            "error": f"HTTPError: {e.code} {e.reason}",
        }
    except Exception as e:
        return {
            "ok": False,
            "status_code": None,
            "content_type": "",
            "final_url": url,
            "raw_text": "",
            "title": "",
            "body_text": "",
            "error": f"{type(e).__name__}: {e}",
        }


def extract_evidence_segments(body_text: str):
    raw_segments = re.split(r"[\n\r]+|(?<=[。！？!?\.])\s+", body_text or "")
    cleaned = []
    seen = set()

    keyword_re = re.compile(
        r"(revenue|annual|report|filing|official|company|founded|products?|services?|customers?|employees?|investor|canonical|ubuntu|cloud|ai|公告|财报|年报|官网|公司|产品|服务|收入|增长|发布|客户|员工)",
        re.IGNORECASE,
    )

    for seg in raw_segments:
        text = normalize_text(seg)
        if len(text) < 30:
            continue
        if text in seen:
            continue
        seen.add(text)
        score = 0
        if re.search(r"\d", text):
            score += 2
        if keyword_re.search(text):
            score += 1
        cleaned.append((score, text))

    cleaned.sort(key=lambda x: (-x[0], -len(x[1])))
    picked = [x[1] for x in cleaned[:8]]

    if not picked:
        fallback = []
        for seg in raw_segments:
            text = normalize_text(seg)
            if len(text) >= 30 and text not in fallback:
                fallback.append(text)
            if len(fallback) >= 5:
                break
        picked = fallback

    return picked


def default_sources_from_request(req: dict):
    if isinstance(req.get("sources"), list) and req.get("sources"):
        return req["sources"]

    domain = (req.get("domain") or "").strip()
    entity = (req.get("entity") or req.get("company_name") or "Unknown").strip()
    if not domain:
        return []

    url = f"https://{domain}/"
    return [{
        "source_name": f"{entity} Official Website",
        "source_type": "official_website",
        "url": url,
        "title": f"{entity} Homepage",
        "publisher": entity,
        "official_flag": True,
    }]


def ensure_company(cur, entity: str, domain: str, region: str):
    cur.execute("""
        SET search_path TO insight,public;
        SELECT id, company_code, company_name, domain, region, status
        FROM company
        WHERE lower(company_name)=lower(%s)
           OR (domain IS NOT NULL AND lower(domain)=lower(%s))
        ORDER BY id ASC
        LIMIT 1
    """, (entity, domain))
    row = cur.fetchone()
    if row:
        return {
            "action": "existing",
            "company": {
                "id": row[0],
                "company_code": row[1],
                "company_name": row[2],
                "domain": row[3],
                "region": row[4],
                "status": row[5],
            }
        }

    company_code = f"{safe_slug(domain or entity)}-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO company(company_code, company_name, domain, region, status)
        VALUES (%s,%s,%s,%s,'active')
        RETURNING id, company_code, company_name, domain, region, status
    """, (company_code, entity, domain or None, region or None))
    row = cur.fetchone()
    return {
        "action": "inserted",
        "company": {
            "id": row[0],
            "company_code": row[1],
            "company_name": row[2],
            "domain": row[3],
            "region": row[4],
            "status": row[5],
        }
    }


def ensure_source(cur, source_name: str, source_type: str, root_domain: str, publisher: str, official_flag: bool):
    cur.execute("""
        SET search_path TO insight,public;
        SELECT id, source_code, source_name, source_type, root_domain, official_flag
        FROM source
        WHERE lower(source_name)=lower(%s)
          AND lower(source_type)=lower(%s)
          AND coalesce(lower(root_domain),'')=coalesce(lower(%s),'')
        ORDER BY id ASC
        LIMIT 1
    """, (source_name, source_type, root_domain or ""))
    row = cur.fetchone()
    if row:
        return {
            "action": "existing",
            "source": {
                "id": row[0],
                "source_code": row[1],
                "source_name": row[2],
                "source_type": row[3],
                "root_domain": row[4],
                "official_flag": row[5],
            }
        }

    source_code = f"{safe_slug(source_type)}-{safe_slug(source_name)}-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO source(source_code, source_name, source_type, root_domain, publisher, official_flag)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id, source_code, source_name, source_type, root_domain, official_flag
    """, (source_code, source_name, source_type, root_domain or None, publisher or None, bool(official_flag)))
    row = cur.fetchone()
    return {
        "action": "inserted",
        "source": {
            "id": row[0],
            "source_code": row[1],
            "source_name": row[2],
            "source_type": row[3],
            "root_domain": row[4],
            "official_flag": row[5],
        }
    }


def insert_analysis_run(cur, company_id: int):
    run_code = f"official-source-ingest-{uuid.uuid4().hex[:8]}"
    request_id = str(uuid.uuid4())
    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO analysis_run(run_code, request_id, analysis_type, target_company_id)
        VALUES (%s,%s,%s,%s)
        RETURNING id, run_code, request_id, analysis_type, target_company_id
    """, (run_code, request_id, "official_source_ingest", company_id))
    row = cur.fetchone()
    return {
        "id": row[0],
        "run_code": row[1],
        "request_id": row[2],
        "analysis_type": row[3],
        "target_company_id": row[4],
    }


def insert_source_snapshot(cur, source_id: int, company_id: int, snapshot: dict):
    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO source_snapshot(
            source_id,
            company_id,
            snapshot_type,
            snapshot_title,
            snapshot_url,
            snapshot_time,
            fetch_time,
            content_hash,
            raw_storage_path,
            parsed_text_storage_path,
            metadata_json
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        RETURNING id
    """, (
        source_id,
        company_id,
        snapshot["snapshot_type"],
        snapshot["snapshot_title"],
        snapshot["snapshot_url"],
        snapshot["snapshot_time"],
        snapshot["fetch_time"],
        snapshot["content_hash"],
        snapshot["raw_storage_path"],
        snapshot["parsed_text_storage_path"],
        json.dumps(to_jsonable(snapshot["metadata_json"]), ensure_ascii=False),
    ))
    return cur.fetchone()[0]


def insert_evidence_item(cur, source_snapshot_id: int, company_id: int, title: str, text: str, evidence_type: str, confidence_score: float):
    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO evidence_item(
            source_snapshot_id,
            company_id,
            evidence_type,
            evidence_title,
            evidence_text,
            evidence_date,
            confidence_score
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        source_snapshot_id,
        company_id,
        evidence_type,
        title,
        text,
        utc_now().date(),
        confidence_score,
    ))
    return cur.fetchone()[0]


def insert_metric_observation(cur, company_id: int, source_snapshot_id: int, evidence_item_id: int, metric_code: str, metric_name: str, metric_value: float, metric_unit: str):
    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO metric_observation(
            company_id,
            metric_code,
            metric_name,
            metric_value,
            metric_unit,
            period_type,
            observation_date,
            source_snapshot_id,
            evidence_item_id
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        company_id,
        metric_code,
        metric_name,
        metric_value,
        metric_unit,
        "point_in_time",
        utc_now().date(),
        source_snapshot_id,
        evidence_item_id,
    ))
    return cur.fetchone()[0]


def build_snapshot_plan(req: dict):
    entity = (req.get("entity") or req.get("company_name") or "Unknown").strip()
    domain = (req.get("domain") or "").strip()
    region = (req.get("region") or "").strip()
    ts_dir = utc_now().strftime("%Y%m%d_%H%M%S")
    entity_slug = safe_slug(domain or entity)
    base_dir = ROOT / "outputs" / "insight_ingest" / entity_slug / ts_dir

    plans = []
    for idx, src in enumerate(default_sources_from_request(req), start=1):
        source_name = (src.get("source_name") or f"{entity} Source {idx}").strip()
        source_type = (src.get("source_type") or "official_website").strip()
        url = (src.get("url") or "").strip()
        publisher = (src.get("publisher") or entity).strip()
        official_flag = bool(src.get("official_flag", True))

        fetch_result = fetch_url(url) if url else {
            "ok": False,
            "status_code": None,
            "content_type": "",
            "final_url": url,
            "raw_text": "",
            "title": "",
            "body_text": "",
            "error": "url_missing",
        }

        parsed_title = normalize_text(src.get("title") or fetch_result.get("title") or f"{entity} Source Capture")
        parsed_body = (fetch_result.get("body_text") or "").strip()
        raw_text = fetch_result.get("raw_text") or ""

        if not parsed_body:
            parsed_body = "\n".join([
                f"title: {parsed_title}",
                f"url: {url}",
                f"source_type: {source_type}",
                f"publisher: {publisher}",
                f"captured_at: {utc_now_iso()}",
                f"fetch_error: {fetch_result.get('error') or ''}",
            ]).strip()

        raw_storage_path = base_dir / f"source_{idx:02d}_raw.json"
        parsed_storage_path = base_dir / f"source_{idx:02d}_parsed.txt"

        raw_payload = {
            "entity": entity,
            "domain": domain,
            "region": region,
            "source_name": source_name,
            "source_type": source_type,
            "url": url,
            "publisher": publisher,
            "official_flag": official_flag,
            "fetch_result": {
                "ok": fetch_result.get("ok"),
                "status_code": fetch_result.get("status_code"),
                "content_type": fetch_result.get("content_type"),
                "final_url": fetch_result.get("final_url"),
                "error": fetch_result.get("error"),
            },
            "captured_at": utc_now_iso(),
        }

        dump_json(raw_storage_path, raw_payload)
        dump_text(parsed_storage_path, parsed_body)

        evidence_segments = extract_evidence_segments(parsed_body)
        if not evidence_segments:
            evidence_segments = [parsed_body[:1200]]

        plans.append({
            "source_name": source_name,
            "source_type": source_type,
            "url": url,
            "publisher": publisher,
            "official_flag": official_flag,
            "root_domain": domain or "",
            "snapshot_type": source_type,
            "snapshot_title": parsed_title,
            "snapshot_url": fetch_result.get("final_url") or url,
            "snapshot_time": utc_now_iso(),
            "fetch_time": utc_now_iso(),
            "content_hash": text_hash(raw_text or parsed_body),
            "raw_storage_path": str(raw_storage_path.relative_to(ROOT)),
            "parsed_text_storage_path": str(parsed_storage_path.relative_to(ROOT)),
            "parsed_text": parsed_body,
            "fetch_ok": bool(fetch_result.get("ok")),
            "fetch_error": fetch_result.get("error"),
            "status_code": fetch_result.get("status_code"),
            "content_type": fetch_result.get("content_type"),
            "evidence_segments": evidence_segments,
            "metadata_json": {
                "entity": entity,
                "domain": domain,
                "region": region,
                "source_name": source_name,
                "source_type": source_type,
                "publisher": publisher,
                "official_flag": official_flag,
                "fetch_ok": bool(fetch_result.get("ok")),
                "fetch_error": fetch_result.get("error"),
                "status_code": fetch_result.get("status_code"),
                "content_type": fetch_result.get("content_type"),
            },
        })

    return plans


def build_output(req: dict, company_record: dict, run_row: dict | None, plan_rows: list, dry_run: bool):
    source_count = len(plan_rows)
    evidence_count = sum(len(x.get("evidence_segments") or []) for x in plan_rows)
    metric_count = sum(2 for _ in plan_rows)

    if dry_run:
        conclusion = "official_source_ingest_skill dry-run ready; live fetch + body extraction + DB write plan resolved."
        facts = [
            "This dry-run performs live fetch when source url is reachable.",
            "Local raw/parsed snapshot files are already materialized.",
            "DB write target for this step is company/source/source_snapshot/analysis_run/evidence_item/metric_observation/citation_link.",
        ]
        next_steps = [
            "Run without --dry-run to persist into insight schema.",
            "Inspect parsed_text quality and extracted evidence segments.",
            "Then add citation_link on top of extracted evidence.",
        ]
    else:
        conclusion = "official_source_ingest_skill real-write succeeded; live fetch + body extraction data persisted into insight schema."
        facts = [
            "Company record ensured in insight.company.",
            "Source records ensured in insight.source.",
            "Snapshot rows inserted into insight.source_snapshot.",
            "Analysis run row inserted into insight.analysis_run.",
            "Extracted evidence rows inserted into insight.evidence_item.",
            "Derived metric rows inserted into insight.metric_observation.",
            "Citation rows inserted into insight.citation_link.",
        ]
        next_steps = [
            "Verify parsed_text quality in stored snapshots.",
            "Verify citation_link binding for extracted evidence.",
            "Let report_build_skill consume richer evidence rows.",
        ]

    out = {
        "ok": True,
        "skill_name": "official_source_ingest_skill",
        "status": "scaffold",
        "schema_version": "v1",
        "ts": utc_now_iso(),
        "skill_config": skill_cfg(),
        "request": req,
        "conclusion": conclusion,
        "core_data": [
            {"field": "entity", "value": req.get("entity") or req.get("company_name")},
            {"field": "domain", "value": req.get("domain")},
            {"field": "planned_snapshot_count" if dry_run else "written_snapshot_count", "value": source_count},
            {"field": "planned_evidence_count" if dry_run else "written_evidence_count", "value": evidence_count},
            {"field": "planned_metric_count" if dry_run else "written_metric_count", "value": metric_count},
        ],
        "sources": [{"source_type": x["source_type"], "url": x["url"], "fetch_ok": x["fetch_ok"], "fetch_error": x["fetch_error"]} for x in plan_rows],
        "facts": facts,
        "inferences": [
            "Once this write path is stable, company_profile_skill and report_build_skill can consume body-level evidence instead of bootstrap-only placeholders."
        ],
        "hypotheses": [],
        "risks": [
            "Some sites may block fetches or return partial HTML, so parsed_text quality still needs verification.",
            "Deterministic extraction currently favors sentence segments with digits/keywords and may miss subtler evidence."
        ],
        "next_steps": next_steps,
        "source_plan": [],
        "db_write_plan": [
            "company",
            "source",
            "source_snapshot",
            "analysis_run",
            "evidence_item",
            "metric_observation",
        ],
        "artifact_plan": [],
    }

    if company_record:
        out["core_data"].insert(1, {"field": "company_id", "value": company_record["id"]})
    if run_row:
        out["core_data"].insert(2, {"field": "analysis_run_id", "value": run_row["id"]})

    for row in plan_rows:
        item = {
            "source_name": row["source_name"],
            "source_type": row["source_type"],
            "url": row["url"],
            "raw_storage_path": row["raw_storage_path"],
            "parsed_text_storage_path": row["parsed_text_storage_path"],
            "snapshot_time": row["snapshot_time"],
            "fetch_ok": row["fetch_ok"],
            "fetch_error": row["fetch_error"],
            "status_code": row["status_code"],
            "content_type": row["content_type"],
            "evidence_segment_count": len(row.get("evidence_segments") or []),
            "sample_evidence_segments": (row.get("evidence_segments") or [])[:3],
        }
        for key in [
            "company_id", "company_action", "source_id", "source_action",
            "snapshot_id", "evidence_ids", "metric_ids", "analysis_run_id", "run_code"
        ]:
            if key in row:
                item[key] = row[key]
        out["source_plan"].append(item)

    return to_jsonable(out)



def insert_citation_link(cur, request_id: str, run_code: str, source_id: int, source_snapshot_id: int, evidence_item_id: int, citation_label: str, citation_url: str):
    claim_code = f"{run_code}:snapshot_{source_snapshot_id}:evidence_{evidence_item_id}"
    cur.execute("""
        SELECT id
        FROM citation_link
        WHERE claim_code = %s
           OR (evidence_item_id = %s AND source_snapshot_id = %s)
        ORDER BY id ASC
        LIMIT 1
    """, (claim_code, evidence_item_id, source_snapshot_id))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("""
        INSERT INTO citation_link(
            request_id,
            report_id,
            claim_code,
            evidence_item_id,
            source_snapshot_id,
            source_id,
            citation_label,
            citation_url,
            citation_note
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        request_id,
        None,
        claim_code,
        evidence_item_id,
        source_snapshot_id,
        source_id,
        citation_label,
        citation_url,
        "auto_generated_from_official_source_ingest_skill",
    ))
    return cur.fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    req = json.loads(args.input_json)
    if "entity" not in req and "company_name" in req:
        req["entity"] = req["company_name"]

    entity = (req.get("entity") or "").strip()
    if not entity:
        raise SystemExit("entity/company_name is required")

    plan_rows = build_snapshot_plan(req)

    if args.dry_run:
        out = build_output(req, None, None, plan_rows, dry_run=True)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    conn = db_connect()
    try:
        with conn:
            with conn.cursor() as cur:
                company_wrap = ensure_company(
                    cur,
                    entity=entity,
                    domain=(req.get("domain") or "").strip(),
                    region=(req.get("region") or "").strip(),
                )
                company = company_wrap["company"]
                run_row = insert_analysis_run(cur, company["id"])

                persisted = []
                for row in plan_rows:
                    source_wrap = ensure_source(
                        cur,
                        source_name=row["source_name"],
                        source_type=row["source_type"],
                        root_domain=row["root_domain"],
                        publisher=row["publisher"],
                        official_flag=row["official_flag"],
                    )
                    source = source_wrap["source"]

                    snapshot_id = insert_source_snapshot(cur, source["id"], company["id"], row)

                    evidence_ids = []
                    citation_ids = []
                    for idx, seg in enumerate(row.get("evidence_segments") or [], start=1):
                        evidence_type = "body_extract" if row.get("fetch_ok") else "source_capture"
                        evidence_title = f"{row['snapshot_title']} / segment {idx:02d}"
                        evidence_id = insert_evidence_item(
                            cur,
                            source_snapshot_id=snapshot_id,
                            company_id=company["id"],
                            title=evidence_title,
                            text=seg,
                            evidence_type=evidence_type,
                            confidence_score=0.75 if row.get("fetch_ok") else 0.60,
                        )
                        evidence_ids.append(evidence_id)
                        citation_id = insert_citation_link(
                            cur,
                            request_id=run_row["request_id"],
                            run_code=run_row["run_code"],
                            source_id=source["id"],
                            source_snapshot_id=snapshot_id,
                            evidence_item_id=evidence_id,
                            citation_label=f'{row["title"]} / segment {idx:02d}',
                            citation_url=row["url"],
                        )
                        citation_ids.append(citation_id)

                    metric_ids = []
                    if evidence_ids:
                        metric_ids.append(insert_metric_observation(
                            cur,
                            company_id=company["id"],
                            source_snapshot_id=snapshot_id,
                            evidence_item_id=evidence_ids[0],
                            metric_code="official_source_snapshot_count",
                            metric_name="Official Source Snapshot Count",
                            metric_value=1.0,
                            metric_unit="count",
                        ))
                        metric_ids.append(insert_metric_observation(
                            cur,
                            company_id=company["id"],
                            source_snapshot_id=snapshot_id,
                            evidence_item_id=evidence_ids[0],
                            metric_code="extracted_evidence_segment_count",
                            metric_name="Extracted Evidence Segment Count",
                            metric_value=float(len(evidence_ids)),
                            metric_unit="count",
                        ))

                    row = dict(row)
                    row["company_id"] = company["id"]
                    row["company_action"] = company_wrap["action"]
                    row["source_id"] = source["id"]
                    row["source_action"] = source_wrap["action"]
                    row["snapshot_id"] = snapshot_id
                    row["evidence_ids"] = evidence_ids
                    row["metric_ids"] = metric_ids
                    row["citation_ids"] = citation_ids
                    row["analysis_run_id"] = run_row["id"]
                    row["run_code"] = run_row["run_code"]
                    persisted.append(row)

        out = build_output(req, company, run_row, persisted, dry_run=False)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
