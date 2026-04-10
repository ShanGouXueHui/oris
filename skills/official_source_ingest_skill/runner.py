#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import uuid
from io import BytesIO
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
OFFICIAL_INGEST_POLICY_PATH = ROOT / "config" / "official_source_ingest_policy.json"
OFFICIAL_INGEST_RULE_CFG_PATH = ROOT / "config" / "official_ingest_rule_config.json"


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
    s = str(text or "")
    s = s.replace("\x00", " ").replace("\ufeff", " ")
    return re.sub(r"\s+", " ", s).strip()

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




def load_ingest_policy():
    try:
        return load_json(OFFICIAL_INGEST_POLICY_PATH)
    except Exception:
        return {
            "pdf_enabled": True,
            "pdf_max_pages": 25,
            "max_segments_per_source": 12,
            "min_segment_length": 24,
            "noise_substrings": [],
            "prefer_url_keywords": [],
            "evidence_priority_keywords": []
        }


def is_noise_text(text: str):
    s = normalize_text(text).lower()
    if not s:
        return True
    policy = load_ingest_policy()
    for bad in (policy.get("noise_substrings") or []):
        if bad.lower() in s:
            return True
    return False


def extract_pdf_text(raw: bytes):
    policy = load_ingest_policy()
    max_pages = int(policy.get("pdf_max_pages", 30))
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(raw), strict=False)
        try:
            if getattr(reader, "is_encrypted", False):
                reader.decrypt("")
        except Exception:
            pass

        parts = []
        for idx, page in enumerate(reader.pages):
            if idx >= max_pages:
                break

            best = ""
            for mode in ("layout", "plain"):
                try:
                    if mode == "layout":
                        one = page.extract_text(extraction_mode="layout") or ""
                    else:
                        one = page.extract_text() or ""
                except TypeError:
                    try:
                        one = page.extract_text() or ""
                    except Exception:
                        one = ""
                except Exception:
                    one = ""

                one = clean_pdf_text(one)
                if len(one) > len(best):
                    best = one

            if best:
                parts.append(best)

        return clean_pdf_text("\n\n".join(parts))
    except Exception:
        return ""

def load_ingest_policy():
    try:
        return load_json(OFFICIAL_INGEST_POLICY_PATH)
    except Exception:
        return {
            "pdf_enabled": True,
            "pdf_max_pages": 30,
            "max_segments_per_source": 10,
            "min_segment_length": 40,
            "noise_substrings": [],
            "metadata_prefixes": [],
            "evidence_priority_keywords": []
        }


def clean_pdf_text(text: str) -> str:
    s = str(text or "")
    s = s.replace("\x00", " ").replace("\ufeff", " ")
    s = s.replace("\r", "\n")
    s = s.replace("\t", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    while "\n\n\n" in s:
        s = s.replace("\n\n\n", "\n\n")
    return s.strip()


def is_metadata_like_text(text: str) -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    lower = s.lower()
    policy = load_ingest_policy()
    for prefix in (policy.get("metadata_prefixes") or []):
        if lower.startswith(str(prefix).lower()):
            return True
    return False


def is_noise_text(text: str) -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    lower = s.lower()
    policy = load_ingest_policy()
    for bad in (policy.get("noise_substrings") or []):
        if str(bad).lower() in lower:
            return True
    return False

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
            return normalize_text(raw.decode(enc, errors="ignore"))
        except Exception:
            continue
    return normalize_text(raw.decode("utf-8", errors="ignore"))


def run_curl_fetch(url: str, timeout: int = DEFAULT_TIMEOUT):
    import subprocess
    cmd = [
        "curl",
        "-L",
        "--compressed",
        "--max-time", str(timeout),
        "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "-H", "Accept: application/pdf,application/octet-stream;q=0.9,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.9,de;q=0.8,zh-CN;q=0.7",
        "-H", "Referer: https://group.mercedes-benz.com/investors/",
        "-D", "-",
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, check=False)
    if r.returncode != 0:
        return {
            "ok": False,
            "status_code": None,
            "content_type": "",
            "final_url": url,
            "raw_text": "",
            "raw_bytes": b"",
            "title": "",
            "body_text": "",
            "error": f"curl_returncode={r.returncode}",
        }

    raw = r.stdout or b""
    header_end = raw.find(b"\r\n\r\n")
    sep_len = 4
    if header_end < 0:
        header_end = raw.find(b"\n\n")
        sep_len = 2
    if header_end < 0:
        return {
            "ok": False,
            "status_code": None,
            "content_type": "",
            "final_url": url,
            "raw_text": "",
            "raw_bytes": b"",
            "title": "",
            "body_text": "",
            "error": "curl_header_parse_failed",
        }

    header_blob = raw[:header_end].decode("latin-1", errors="ignore")
    body = raw[header_end + sep_len:]

    headers = [x for x in header_blob.splitlines() if x.strip()]
    status_code = None
    content_type = ""
    final_url = url

    for line in headers:
        low = line.lower()
        if low.startswith("http/"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                status_code = int(parts[1])
        elif low.startswith("content-type:"):
            content_type = line.split(":", 1)[1].strip()
        elif low.startswith("location:"):
            final_url = line.split(":", 1)[1].strip()

    text_body = ""
    title = ""
    parsed_body = ""

    lowered_ct = (content_type or "").lower()
    if "pdf" in lowered_ct or url.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(body))
            pages = []
            for page in reader.pages[:15]:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    pages.append("")
            parsed_body = "\n".join([x for x in pages if x]).replace("\x00", " ")
            parsed_body = " ".join(parsed_body.split())
            title = url.split("/")[-1]
            text_body = parsed_body
        except Exception as e:
            return {
                "ok": False,
                "status_code": status_code,
                "content_type": content_type,
                "final_url": final_url,
                "raw_text": "",
                "raw_bytes": body,
                "title": "",
                "body_text": "",
                "error": f"pdf_parse_error: {type(e).__name__}: {e}",
            }
    else:
        text_body = decode_bytes(body, content_type)
        if "html" in lowered_ct or "<html" in text_body.lower():
            parser = HTMLTextExtractor()
            parser.feed(text_body)
            title, parsed_body = parser.result()
        else:
            parsed_body = text_body
            title = ""

    return {
        "ok": True,
        "status_code": status_code or 200,
        "content_type": content_type,
        "final_url": final_url,
        "raw_text": text_body[:200000] if isinstance(text_body, str) else "",
        "raw_bytes": body,
        "title": title,
        "body_text": (parsed_body or "").replace("\x00", " "),
        "error": None,
    }



def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT):
    curl_out = run_curl_fetch(url, timeout=timeout)
    if curl_out.get("ok"):
        return curl_out

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
                "raw_bytes": raw,
                "title": title,
                "body_text": body.replace("\x00", " ") if isinstance(body, str) else "",
                "error": None,
            }
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "status_code": e.code,
            "content_type": "",
            "final_url": url,
            "raw_text": "",
            "raw_bytes": b"",
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
            "raw_bytes": b"",
            "title": "",
            "body_text": "",
            "error": f"{type(e).__name__}: {e}",
        }


def extract_evidence_segments(body_text: str):
    policy = load_ingest_policy()
    min_len = int(policy.get("min_segment_length", 40))
    max_segments = int(policy.get("max_segments_per_source", 10))
    priority_words = [str(x).lower() for x in (policy.get("evidence_priority_keywords") or [])]

    raw_segments = re.split(r"[\n\r]+|(?<=[。！？!?\.])\s+", body_text or "")
    cleaned = []
    seen = set()

    for seg in raw_segments:
        one = clean_pdf_text(seg)
        if len(one) < min_len:
            continue
        if "\x00" in one:
            continue
        if is_metadata_like_text(one):
            continue
        if is_noise_text(one):
            continue
        if one in seen:
            continue
        seen.add(one)

        score = 0
        lower = one.lower()

        if re.search(r"\d", one):
            score += 2
        if re.search(r"\b(202[0-9]|19[0-9]{2}|20[0-9]{2})\b", one):
            score += 1
        if "%" in one or "€" in one or "$" in one or "亿元" in one or "万辆" in one or "million" in lower or "billion" in lower:
            score += 2

        for kw in priority_words:
            if kw and kw in lower:
                score += 2

        if len(one) >= 80:
            score += 1
        if len(one) >= 160:
            score += 1

        cleaned.append((score, one))

    cleaned.sort(key=lambda x: (-x[0], -len(x[1])))
    picked = [x[1] for x in cleaned[:max_segments]]

    if not picked:
        fallback = []
        for seg in raw_segments:
            one = clean_pdf_text(seg)
            if len(one) >= min_len and not is_metadata_like_text(one) and not is_noise_text(one) and one not in fallback:
                fallback.append(one)
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

        fetch_result = fetch_url_providerized(url, timeout=DEFAULT_TIMEOUT) if url else {
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

        weak_body = False
        try:
            weak_body = is_weak_body_text(parsed_body, parsed_title)
        except Exception:
            weak_body = False

        if weak_body:
            fetch_result = dict(fetch_result)
            fetch_result["ok"] = False
            fetch_result["error"] = fetch_result.get("error") or "weak_body_text"
            parsed_body = ""

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

        evidence_segments = []
        if fetch_result.get("ok"):
            evidence_segments = extract_evidence_segments(parsed_body)

        if not evidence_segments and fetch_result.get("ok"):
            fallback_seg = (parsed_body or "")[:1200].strip()
            if fallback_seg and not is_weak_body_text(fallback_seg, parsed_title):
                evidence_segments = [fallback_seg]

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
    if dry_run:
        evidence_count = sum(len(x.get("evidence_segments") or []) for x in plan_rows)
        metric_count = sum(2 for _ in plan_rows)
        citation_count = evidence_count
    else:
        evidence_count = sum(len(x.get("evidence_ids") or []) for x in plan_rows)
        metric_count = sum(len(x.get("metric_ids") or []) for x in plan_rows)
        citation_count = sum(len(x.get("citation_ids") or []) for x in plan_rows)

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
            {"field": "planned_citation_count" if dry_run else "written_citation_count", "value": citation_count},
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
            "citation_link",
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
            "snapshot_id", "evidence_ids", "metric_ids", "citation_ids", "analysis_run_id", "run_code"
        ]:
            if key in row:
                item[key] = row[key]
        if "citation_ids" not in item:
            item["citation_ids"] = row.get("citation_ids") or []
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



# === FORCED_FETCH_V2_START ===
import subprocess
import tempfile
import shutil

def _ff2_strip_nul(text: str) -> str:
    return (text or "").replace("\x00", "")

def _ff2_clean_text(text: str) -> str:
    text = _ff2_strip_nul(text).replace("\r", "\n")
    lines = [x.strip() for x in text.splitlines()]
    lines = [x for x in lines if x]
    return "\n".join(lines).strip()

def _ff2_is_pdf(url: str, content_type: str = "") -> bool:
    u = (url or "").lower()
    c = (content_type or "").lower()
    return u.endswith(".pdf") or ".pdf?" in u or "application/pdf" in c

def _ff2_parse_html_text(text: str):
    parser = HTMLTextExtractor()
    parser.feed(text)
    title, body = parser.result()
    return title, body

def _ff2_extract_pdf_text_from_file(pdf_path: str) -> str:
    text = ""

    if shutil.which("pdftotext"):
        txt_path = pdf_path + ".txt"
        r = subprocess.run(
            ["pdftotext", "-layout", pdf_path, txt_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if Path(txt_path).exists():
            text = Path(txt_path).read_text(encoding="utf-8", errors="ignore")

    if not _ff2_clean_text(text):
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            parts = []
            for page in reader.pages[:400]:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    continue
            text = "\n".join(parts)
        except Exception:
            text = ""

    return _ff2_clean_text(text)

def _ff2_curl_fetch(url: str, timeout: int = DEFAULT_TIMEOUT):
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

    with tempfile.TemporaryDirectory(prefix="oris_ff2_") as td:
        body_path = Path(td) / "body.bin"
        meta_path = Path(td) / "meta.txt"

        cmd = [
            "curl",
            "-L",
            "--compressed",
            "-sS",
            "-A", ua,
            "-H", "Accept: text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-o", str(body_path),
            "-D", str(meta_path),
            "--max-time", str(timeout),
            url,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)

        raw = body_path.read_bytes() if body_path.exists() else b""
        headers = meta_path.read_text(encoding="utf-8", errors="ignore") if meta_path.exists() else ""

        content_type = ""
        final_url = url
        status_code = None

        for line in headers.splitlines():
            low = line.lower()
            if low.startswith("content-type:"):
                content_type = line.split(":", 1)[1].strip()
            elif low.startswith("location:"):
                final_url = line.split(":", 1)[1].strip()

        if r.returncode == 0 and raw:
            return {
                "ok": True,
                "status_code": 200,
                "content_type": content_type,
                "final_url": final_url or url,
                "raw_bytes": raw,
                "error": None,
            }

        return {
            "ok": False,
            "status_code": status_code,
            "content_type": content_type,
            "final_url": final_url or url,
            "raw_bytes": raw,
            "error": (r.stderr or "").strip() or "curl_fetch_failed",
        }

def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT):
    # force curl-first; only fallback to urllib if curl binary is unavailable
    if shutil.which("curl"):
        c = _ff2_curl_fetch(url, timeout=timeout)
        if c.get("ok"):
            raw = c.get("raw_bytes") or b""
            content_type = c.get("content_type") or ""
            final_url = c.get("final_url") or url

            if _ff2_is_pdf(final_url, content_type):
                with tempfile.TemporaryDirectory(prefix="oris_ff2_pdf_") as td:
                    pdf_path = Path(td) / "source.pdf"
                    pdf_path.write_bytes(raw)
                    body = _ff2_extract_pdf_text_from_file(str(pdf_path))
                title = ""
                if body:
                    for line in body.splitlines():
                        one = normalize_text(line)
                        if len(one) >= 8:
                            title = one[:200]
                            break
                if not title:
                    title = Path(final_url).name or "PDF Document"
                return {
                    "ok": True,
                    "status_code": 200,
                    "content_type": content_type or "application/pdf",
                    "final_url": final_url,
                    "raw_text": "",
                    "title": title,
                    "body_text": body,
                    "error": None,
                }

            text_body = decode_bytes(raw, content_type)
            title, body = _ff2_parse_html_text(text_body)
            return {
                "ok": True,
                "status_code": 200,
                "content_type": content_type,
                "final_url": final_url,
                "raw_text": _ff2_strip_nul(text_body),
                "title": title,
                "body_text": _ff2_strip_nul(body),
                "error": None,
            }

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

            if _ff2_is_pdf(final_url, content_type):
                with tempfile.TemporaryDirectory(prefix="oris_ff2_pdf_") as td:
                    pdf_path = Path(td) / "source.pdf"
                    pdf_path.write_bytes(raw)
                    body = _ff2_extract_pdf_text_from_file(str(pdf_path))
                title = ""
                if body:
                    for line in body.splitlines():
                        one = normalize_text(line)
                        if len(one) >= 8:
                            title = one[:200]
                            break
                if not title:
                    title = Path(final_url).name or "PDF Document"
                return {
                    "ok": True,
                    "status_code": status_code,
                    "content_type": content_type or "application/pdf",
                    "final_url": final_url,
                    "raw_text": "",
                    "title": title,
                    "body_text": body,
                    "error": None,
                }

            text_body = decode_bytes(raw, content_type)
            title, body = _ff2_parse_html_text(text_body)
            return {
                "ok": True,
                "status_code": status_code,
                "content_type": content_type,
                "final_url": final_url,
                "raw_text": _ff2_strip_nul(text_body),
                "title": title,
                "body_text": _ff2_strip_nul(body),
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
# === FORCED_FETCH_V2_END ===


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

                total_citation_count = 0

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
                        citation_base_title = (
                            row.get("title")
                            or row.get("snapshot_title")
                            or row.get("source_name")
                            or source.get("source_name")
                            or source.get("title")
                            or "source_segment"
                        )
                        citation_url = (
                            row.get("url")
                            or row.get("snapshot_url")
                            or source.get("url")
                            or ""
                        )
                        citation_id = insert_citation_link(
                            cur,
                            request_id=run_row["request_id"],
                            run_code=run_row["run_code"],
                            source_id=source["id"],
                            source_snapshot_id=snapshot_id,
                            evidence_item_id=evidence_id,
                            citation_label=f'{citation_base_title} / segment {idx:02d}',
                            citation_url=citation_url,
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
                    total_citation_count += len(citation_ids)
                    row["analysis_run_id"] = run_row["id"]
                    row["run_code"] = run_row["run_code"]
                    persisted.append(row)

        out = build_output(req, company, run_row, persisted, dry_run=False)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        conn.close()




# === V5_FETCH_AND_SEGMENT_OVERRIDE_START ===
import subprocess as _sp
import tempfile as _tf
import shutil as _sh

def clean_pdf_text(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def is_metadata_like_text(text: str) -> bool:
    low = normalize_text(text).lower()
    if not low:
        return True
    if len(low) < 35:
        return True
    bad_prefixes = (
        "title:",
        "url:",
        "publisher:",
        "source_type:",
        "captured_at:",
        "fetch_error:",
    )
    if any(low.startswith(x) for x in bad_prefixes):
        return True
    bad_terms = (
        "cookies",
        "privacy",
        "unsubscribe",
        "email alert",
        "contact sales",
        "opens in new window",
    )
    if any(x in low for x in bad_terms):
        return True
    return False

def _browser_headers():
    return {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

def _curl_fetch_bytes(url: str, timeout: int):
    cmd = [
        "curl",
        "-L",
        "--compressed",
        "-A", _browser_headers()["User-Agent"],
        "-H", f'Accept: {_browser_headers()["Accept"]}',
        "-H", f'Accept-Language: {_browser_headers()["Accept-Language"]}',
        "--connect-timeout", str(min(int(timeout), 15)),
        "--max-time", str(int(timeout)),
        "-fsSL",
        url,
    ]
    r = _sp.run(cmd, capture_output=True, text=False, check=False)
    if r.returncode == 0 and r.stdout:
        return {"ok": True, "raw": r.stdout, "error": None}
    err = (r.stderr or r.stdout or b"").decode("utf-8", errors="ignore")[:600]
    return {"ok": False, "raw": b"", "error": f"curl_failed: {err}"}

def _parse_html_or_text(raw: bytes, content_type: str):
    text = decode_bytes(raw, content_type or "text/html")
    parser = HTMLTextExtractor()
    parser.feed(text)
    title, body = parser.result()
    body = clean_pdf_text(body or text)
    return {
        "raw_text": text,
        "title": title or "",
        "body_text": body,
    }

def _guess_pdf_title(text: str, url: str):
    for line in (text or "").splitlines():
        s = normalize_text(line)
        if len(s) >= 8:
            return s[:180]
    return Path(url.split("?", 1)[0]).name or "PDF"

def _pdf_text_from_bytes(raw: bytes) -> str:
    pdf_text = ""
    with _tf.TemporaryDirectory() as td:
        td = Path(td)
        pdf_path = td / "tmp.pdf"
        txt_path = td / "tmp.txt"
        pdf_path.write_bytes(raw)

        if _sh.which("pdftotext"):
            r = _sp.run(
                ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
                capture_output=True,
                text=False,
                check=False,
            )
            if r.returncode == 0 and txt_path.exists():
                try:
                    pdf_text = txt_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pdf_text = txt_path.read_text(errors="ignore")

        if not pdf_text:
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_path))
                pages = []
                for page in reader.pages:
                    try:
                        pages.append(page.extract_text() or "")
                    except Exception:
                        continue
                pdf_text = "\n".join(pages)
            except Exception:
                pdf_text = ""

    return clean_pdf_text(pdf_text)

def fetch_url_shadowed_postfix_1(url: str, timeout: int = DEFAULT_TIMEOUT):
    first_error = None
    is_pdf = url.lower().split("?", 1)[0].endswith(".pdf")

    if not is_pdf:
        req = urllib.request.Request(url, headers=_browser_headers())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                final_url = resp.geturl()
                status_code = getattr(resp, "status", 200)

                if "application/pdf" in (content_type or "").lower() or raw[:4] == b"%PDF":
                    pdf_text = _pdf_text_from_bytes(raw)
                    if pdf_text:
                        return {
                            "ok": True,
                            "status_code": status_code,
                            "content_type": "application/pdf",
                            "final_url": final_url,
                            "raw_text": pdf_text,
                            "title": _guess_pdf_title(pdf_text, final_url),
                            "body_text": pdf_text,
                            "error": None,
                        }

                parsed = _parse_html_or_text(raw, content_type)
                if normalize_text(parsed["body_text"]):
                    return {
                        "ok": True,
                        "status_code": status_code,
                        "content_type": content_type,
                        "final_url": final_url,
                        "raw_text": parsed["raw_text"],
                        "title": parsed["title"],
                        "body_text": parsed["body_text"],
                        "error": None,
                    }
        except Exception as e:
            first_error = f"{type(e).__name__}: {e}"

    curl_res = _curl_fetch_bytes(url, timeout)
    if curl_res["ok"]:
        raw = curl_res["raw"]
        final_url = url

        if is_pdf or raw[:4] == b"%PDF":
            pdf_text = _pdf_text_from_bytes(raw)
            if normalize_text(pdf_text):
                return {
                    "ok": True,
                    "status_code": 200,
                    "content_type": "application/pdf",
                    "final_url": final_url,
                    "raw_text": pdf_text,
                    "title": _guess_pdf_title(pdf_text, final_url),
                    "body_text": pdf_text,
                    "error": None,
                }

        parsed = _parse_html_or_text(raw, "text/html")
        if normalize_text(parsed["body_text"]):
            return {
                "ok": True,
                "status_code": 200,
                "content_type": "text/html",
                "final_url": final_url,
                "raw_text": parsed["raw_text"],
                "title": parsed["title"],
                "body_text": parsed["body_text"],
                "error": None,
            }

    return {
        "ok": False,
        "status_code": None,
        "content_type": "",
        "final_url": url,
        "raw_text": "",
        "title": "",
        "body_text": "",
        "error": first_error or curl_res["error"] or "fetch_failed",
    }

def extract_evidence_segments(body_text: str):
    text = clean_pdf_text(body_text)
    raw_segments = re.split(r'[\n\r]+|(?<=[。！？!?\.])\s+', text or "")
    seen = set()
    scored = []

    key_re = re.compile(
        r"(revenue|ebit|free cash flow|gross profit|net liquidity|unit sales|employees|dividend|share buyback|guidance|ros|roe|mb\.os|software-defined|automated driving|robotaxi|electric|xev|销量|营收|收入|利润|毛利|现金流|分红|回购)",
        re.I,
    )

    for seg in raw_segments:
        one = normalize_text(seg)
        if not one:
            continue
        if one in seen:
            continue
        seen.add(one)

        if is_metadata_like_text(one):
            continue

        score = 0
        if re.search(r"\d", one):
            score += 2
        if re.search(r"[€$¥%]|\b(?:billion|million|thousand|bn|mn)\b", one, re.I):
            score += 3
        if key_re.search(one):
            score += 3
        if 50 <= len(one) <= 260:
            score += 1
        elif len(one) > 320:
            score -= 1

        if score >= 3:
            scored.append((score, one))

    scored.sort(key=lambda x: (-x[0], -len(x[1])))
    picked = [x[1] for x in scored[:12]]

    if picked:
        return picked

    fallback = []
    for seg in raw_segments:
        one = normalize_text(seg)
        if is_metadata_like_text(one):
            continue
        if len(one) >= 60:
            fallback.append(one)
        if len(fallback) >= 8:
            break
    return fallback
# === V5_FETCH_AND_SEGMENT_OVERRIDE_END ===




# === ORIS_FETCH_QUALITY_OVERRIDE_20260410_START ===
def _qnorm(text: str) -> str:
    return normalize_text(text or "")

def _finance_keywords():
    return [
        "revenue", "revenues", "sales", "gross profit", "operating profit", "operating income",
        "net income", "net profit", "cash flow", "free cash flow", "margin", "cloud", "advertising",
        "youtube", "google cloud", "search", "subscriptions", "users", "mau", "dau",
        "收入", "营收", "利润", "毛利", "毛利率", "现金流", "自由现金流", "云", "广告", "用户", "销量", "交付"
    ]

def is_weak_body_text(body_text: str, title: str = "") -> bool:
    body = _qnorm(body_text)
    ttl = _qnorm(title)
    lower = body.lower()

    if not body:
        return True
    if len(body) < 300:
        return True

    noise_hits = 0
    noise_terms = [
        "privacy", "cookies", "unsubscribe", "email address", "investor alert options",
        "selecting a year value", "upcoming conference appearances", "your information will be processed",
        "skip to content", "back to top", "view all", "opens in new window"
    ]
    for x in noise_terms:
        if x in lower:
            noise_hits += 1

    kw_hits = 0
    for kw in _finance_keywords():
        if kw.lower() in lower:
            kw_hits += 1

    if ttl and body.lower() == ttl.lower():
        return True
    if ttl and body.lower().startswith(ttl.lower()) and len(body) <= max(len(ttl) + 80, 220):
        return True
    if noise_hits >= 2 and kw_hits == 0:
        return True
    if kw_hits == 0 and len(body) < 800:
        return True

    return False

def is_hard_negative_segment(seg: str) -> bool:
    s = _qnorm(seg).lower()
    if not s:
        return True

    bad = [
        "privacy", "cookies", "unsubscribe", "email address", "investor alert options",
        "selecting a year value", "upcoming conference appearances", "your information will be processed",
        "skip to content", "back to top", "view all", "opens in new window",
        "news (includes earnings date announcements", "earnings date announcements",
        "form required accessibility fix", "terms (opens in new window)",
        "about google (opens in new window)", "google products (opens in new window)"
    ]
    if any(x in s for x in bad):
        return True

    if len(s) < 40:
        return True

    return False

def _segment_score(seg: str) -> int:
    s = _qnorm(seg)
    lower = s.lower()
    score = 0

    if any(ch.isdigit() for ch in s):
        score += 3
    if "%" in s:
        score += 2
    if re.search(r"(€|\$|¥|rmb|usd|亿元|万元|million|billion|bn|mn)", s, flags=re.I):
        score += 2

    for kw in _finance_keywords():
        if kw.lower() in lower:
            score += 1

    if len(s) >= 120:
        score += 1

    return score

def extract_evidence_segments(body_text: str):
    text = clean_pdf_text(body_text)
    raw_segments = re.split(r'[\n\r]+|(?<=[。！？!?\.])\s+', text or "")

    policy = load_ingest_policy()
    max_segments = int((policy.get("quality_gate") or {}).get("max_segments", 12))
    min_len = int((policy.get("quality_gate") or {}).get("min_segment_length", 40))
    max_len = int((policy.get("quality_gate") or {}).get("max_segment_length", 1200))

    rows = []
    seen = set()

    for seg in raw_segments:
        s = _qnorm(seg)
        if not s:
            continue
        if len(s) < min_len or len(s) > max_len:
            continue
        if is_hard_negative_segment(s):
            continue

        key = s[:220].lower()
        if key in seen:
            continue
        seen.add(key)

        sc = _segment_score(s)
        if sc < 2:
            continue
        rows.append((sc, s))

    rows.sort(key=lambda x: (-x[0], -len(x[1])))
    picked = [x[1] for x in rows[:max_segments]]

    if picked:
        return picked

    # weak fallback: still try to salvage numeric lines
    fallback = []
    for seg in raw_segments:
        s = _qnorm(seg)
        if not s or len(s) < min_len:
            continue
        if is_hard_negative_segment(s):
            continue
        if any(ch.isdigit() for ch in s):
            fallback.append(s)
        if len(fallback) >= max_segments:
            break
    return fallback

def fetch_url_providerized(url: str, timeout: int = DEFAULT_TIMEOUT):
    candidates = []

    try:
        out_native = native_fetch(url, timeout)
        if out_native:
            candidates.append(("native", out_native))
            if out_native.get("ok") and not is_weak_body_text(out_native.get("body_text") or "", out_native.get("title") or ""):
                return out_native
    except Exception:
        pass

    try:
        out_curl = run_curl_fetch(url, timeout)
        if out_curl:
            candidates.append(("curl", out_curl))
            if out_curl.get("ok") and not is_weak_body_text(out_curl.get("body_text") or "", out_curl.get("title") or ""):
                return out_curl
    except Exception:
        pass

    good = []
    for name, out in candidates:
        if not out:
            continue
        body = _qnorm(out.get("body_text") or "")
        title = _qnorm(out.get("title") or "")
        score = len(body)
        if out.get("ok"):
            score += 1000
        if not is_weak_body_text(body, title):
            score += 5000
        good.append((score, out))

    if good:
        good.sort(key=lambda x: x[0], reverse=True)
        return good[0][1]

    return {
        "ok": False,
        "status_code": None,
        "content_type": "",
        "final_url": url,
        "raw_text": "",
        "body_text": "",
        "title": "",
        "error": "all_fetch_paths_failed"
    }
# === ORIS_FETCH_QUALITY_OVERRIDE_20260410_END ===




# === CONFIG_DRIVEN_INGEST_RULES_START ===
def load_ingest_rule_cfg():
    try:
        return load_json(OFFICIAL_INGEST_RULE_CFG_PATH)
    except Exception:
        return {"version": 1, "policy_defaults": {}, "profiles": {}}

def _rule_profiles(source_type: str = "", url: str = ""):
    out = ["generic"]
    st = (source_type or "").strip()
    u = (url or "").strip().lower()

    if st:
        out.append(f"source_type:{st}")

    if "sec-filings" in u:
        out.append("url_group:sec_filings")

    return out

def _rule_list(field: str, source_type: str = "", url: str = ""):
    cfg = load_ingest_rule_cfg()
    profiles = cfg.get("profiles") or {}
    out = []
    for key in _rule_profiles(source_type=source_type, url=url):
        vals = (profiles.get(key) or {}).get(field) or []
        for v in vals:
            s = str(v).strip()
            if s and s not in out:
                out.append(s)
    return out

def _rule_scalar(field: str, source_type: str = "", url: str = "", default=None):
    cfg = load_ingest_rule_cfg()
    profiles = cfg.get("profiles") or {}
    for key in reversed(_rule_profiles(source_type=source_type, url=url)):
        prof = profiles.get(key) or {}
        if field in prof:
            return prof.get(field)
    return (cfg.get("policy_defaults") or {}).get(field, default)

def load_ingest_policy():
    try:
        base = load_json(OFFICIAL_INGEST_POLICY_PATH)
    except Exception:
        base = {
            "pdf_enabled": True,
            "pdf_max_pages": 30,
            "max_segments_per_source": 10,
            "min_segment_length": 40,
            "noise_substrings": [],
            "metadata_prefixes": [],
            "evidence_priority_keywords": []
        }
    rule_cfg = load_ingest_rule_cfg()
    defaults = rule_cfg.get("policy_defaults") or {}
    out = dict(defaults)
    out.update(base)
    return out

def _ingest_norm(text: str) -> str:
    if "_qnorm" in globals():
        try:
            return _qnorm(text)
        except Exception:
            pass
    return normalize_text(text)

def is_metadata_like_text(text: str, source_type: str = "", url: str = "") -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    lower = s.lower()

    for prefix in _rule_list("metadata_prefixes", source_type=source_type, url=url):
        if lower.startswith(str(prefix).lower()):
            return True

    for token in _rule_list("metadata_substrings", source_type=source_type, url=url):
        if str(token).lower() in lower:
            return True

    return False

def is_noise_text(text: str, source_type: str = "", url: str = "") -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    lower = s.lower()

    policy = load_ingest_policy()
    for bad in (policy.get("noise_substrings") or []):
        if str(bad).lower() in lower:
            return True

    for bad in _rule_list("noise_substrings", source_type=source_type, url=url):
        if str(bad).lower() in lower:
            return True

    return False

def is_weak_body_text(body_text: str, title: str = "", source_type: str = "", url: str = "") -> bool:
    body = _ingest_norm(body_text)
    title_n = _ingest_norm(title)

    if not body:
        return True

    body_lower = body.lower()
    exacts = {str(x).strip().lower() for x in _rule_list("weak_body_exact_texts", source_type=source_type, url=url)}
    if body_lower in exacts:
        return True

    for token in _rule_list("weak_body_substrings", source_type=source_type, url=url):
        if str(token).lower() in body_lower:
            return True

    min_len = int(_rule_scalar("min_meaningful_body_length", source_type=source_type, url=url, default=120) or 120)
    if len(body) < min_len:
        return True

    if title_n and body_lower == title_n.lower():
        return True

    lines = [x.strip() for x in body.splitlines() if x.strip()]
    unique_ratio = (len(set(lines)) / len(lines)) if lines else 1.0
    if len(lines) >= 6 and unique_ratio < 0.45:
        return True

    return False
# === CONFIG_DRIVEN_INGEST_RULES_END ===

if __name__ == "__main__":
    main()
