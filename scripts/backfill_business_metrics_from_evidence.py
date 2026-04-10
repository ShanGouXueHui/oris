BACKFILL_KIND = "business_metric_backfill"
#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
RULE_CFG_PATH = ROOT / "config" / "metric_backfill_rule_config.json"
INSIGHT_STORAGE_PATH = ROOT / "config" / "insight_storage.json"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_rule_cfg():
    try:
        return json.loads(RULE_CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "business_metric_backfill": {}, "foundation_model_metric_backfill": {}}

def profile_rule_block(kind: str, focus_profile: str):
    cfg = load_rule_cfg()
    block = (cfg.get(kind) or {}).get("company_profiles") or {}
    return block.get(focus_profile) or {}

def compiled_metric_rules(kind: str, focus_profile: str):
    block = profile_rule_block(kind, focus_profile)
    out = []
    for item in (block.get("metric_patterns") or []):
        one = dict(item)
        one["patterns"] = [str(x) for x in (item.get("patterns") or []) if str(x).strip()]
        out.append(one)
    return out

def exclude_patterns(kind: str, focus_profile: str):
    block = profile_rule_block(kind, focus_profile)
    return [str(x).lower() for x in (block.get("exclude_patterns") or [])]


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

def norm(x):
    return str(x or "").strip()

def slugify_metric_code(label: str):
    s = norm(label).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "metric"

def unit_scale_to_value(value_str: str, scale: str):
    try:
        v = float(value_str.replace(",", "").strip())
    except Exception:
        return None
    scale = norm(scale).lower()
    if scale in {"billion", "bn"}:
        return v
    if scale in {"million", "mn"}:
        return v
    return v

def metric_name_from_label(label: str):
    label = norm(label)
    mapping = {
        "consolidated alphabet": "Alphabet Revenue",
        "alphabet": "Alphabet Revenue",
        "google cloud": "Google Cloud Revenue",
        "google services": "Google Services Revenue",
        "domestic games": "Domestic Games Revenue",
        "international games": "International Games Revenue",
        "social networks": "Social Networks Revenue",
        "marketing services": "Marketing Services Revenue",
        "vas": "VAS Revenue",
        "fintech and business services": "FinTech and Business Services Revenue",
        "total revenues": "Total Revenue",
        "gross profit": "Gross Profit",
        "operating profit": "Operating Profit",
        "net profit": "Net Profit",
        "free cash flow": "Free Cash Flow",
        "google advertising": "Google Advertising Revenue",
        "youtube ads": "YouTube Ads Revenue",
        "google search & other": "Google Search & Other Revenue",
    }
    return mapping.get(label.lower(), label.title())

def metric_is_reasonable(code, value, unit):
    try:
        v = float(value)
    except Exception:
        return False

    code = norm(code).lower()
    unit = norm(unit)

    if unit == "percent" and not (0 <= v <= 1000):
        return False

    if code == "advertising_revenue_share" and not (0 <= v <= 100):
        return False

    if code == "gemini_users" and not (0 < v <= 10):
        return False

    if code == "paid_subscriptions" and not (0 < v <= 5000):
        return False

    if code == "google_cloud_revenue":
        if unit == "USD_billion" and not (0 < v <= 500):
            return False
        if unit == "USD_million" and v > 50000:
            return False

    if code == "google_services_revenue":
        if unit == "USD_billion" and not (0 < v <= 500):
            return False
        if unit == "USD_million" and v > 500000:
            return False

    if code == "google_search_and_other_revenue":
        if unit == "USD_million" and not (0 < v <= 500000):
            return False

    if code.endswith("_yoy") and unit == "percent" and not (-100 <= v <= 1000):
        return False

    return True

def add_metric(out, code, name, value, unit):
    if value is None:
        return
    if not metric_is_reasonable(code, value, unit):
        return
    out.append({
        "metric_code": code,
        "metric_name": name,
        "metric_value": float(value),
        "metric_unit": unit,
    })

def extract_metrics_from_text(text: str):
    t = norm(text)
    if not t:
        return []

    out = []

    # Narrative revenue/profit patterns
    narrative_patterns = [
        r'(?P<label>Google Cloud|Google Services|Consolidated Alphabet|Alphabet|Domestic Games|International Games|Social Networks|Marketing Services|VAS|FinTech and Business Services)[^.\n]{0,180}?revenues?\s+(?:increased|rose|grew)\s+(?P<yoy>\d+(?:\.\d+)?)%\s+(?:to|by)\s+(?P<currency>RMB|USD|US\$|\$|€)?\s?(?P<value>[\d\.,]+)\s*(?P<scale>billion|million|bn|mn)',
        r'(?P<label>Total revenues|Gross profit|Operating profit|Net profit|Free cash flow)[^.\n]{0,120}?\s(?:was|were)\s+(?P<currency>RMB|USD|US\$|\$|€)?\s?(?P<value>[\d\.,]+)\s*(?P<scale>billion|million|bn|mn)[^.\n]{0,80}?(?:up|grew|increased)\s+(?P<yoy>\d+(?:\.\d+)?)%',
        r'(?P<label>Google advertising|YouTube ads|Google Search & other|Google Cloud|Other Bets)[^.\n]{0,80}?\$\s?(?P<prev>[\d,]+)\s+\$\s?(?P<value>[\d,]+)',
    ]

    for pat in narrative_patterns:
        for m in re.finditer(pat, t, flags=re.I):
            gd = m.groupdict()
            label = norm(gd.get("label"))
            if not label:
                continue
            name = metric_name_from_label(label)
            code = slugify_metric_code(name)

            if gd.get("value"):
                value = unit_scale_to_value(gd["value"], gd.get("scale") or "")
                unit = "USD_billion"
                if norm(gd.get("currency")).upper() == "RMB":
                    unit = "RMB_billion"
                if norm(gd.get("scale")).lower() in {"million", "mn"}:
                    unit = "USD_million" if unit.startswith("USD") else "RMB_million"
                if gd.get("prev") and not gd.get("scale"):
                    # tabular dollar line, treat as million
                    value = float(gd["value"].replace(",", ""))
                    unit = "USD_million"
                add_metric(out, code, name, value, unit)

            if gd.get("yoy"):
                add_metric(out, f"{code}_yoy", f"{name} YoY", float(gd["yoy"]), "percent")

    # Alphabet-specific scale/user metrics
    m = re.search(r'over\s+([\d\.,]+)\s+million paid subscriptions', t, flags=re.I)
    if m:
        add_metric(out, "paid_subscriptions", "Paid Subscriptions", float(m.group(1).replace(",", "")), "million_accounts")

    if re.search(r'half a billion users', t, flags=re.I):
        add_metric(out, "gemini_users", "Gemini Users", 0.5, "billion_users")

    m = re.search(r'more than\s+([\d\.,]+)% of total revenues? from online advertising', t, flags=re.I)
    if m:
        add_metric(out, "advertising_revenue_share", "Advertising Revenue Share", float(m.group(1).replace(",", "")), "percent")

    # Tencent style summary line
    m = re.search(r'Revenues:\s*\+?([\d\.]+)%\s*YoY,\s*gross profit:\s*\+?([\d\.]+)%\s*YoY,\s*non-IFRS operating profit:\s*\+?([\d\.]+)%\s*YoY', t, flags=re.I)
    if m:
        add_metric(out, "revenue_yoy", "Revenue YoY", float(m.group(1)), "percent")
        add_metric(out, "gross_profit_yoy", "Gross Profit YoY", float(m.group(2)), "percent")
        add_metric(out, "operating_profit_yoy", "Operating Profit YoY", float(m.group(3)), "percent")

    # Agent / model company benchmark style
    m = re.search(r'over\s+(\d+)\s+step', t, flags=re.I)
    if m:
        add_metric(out, "agent_task_steps", "Agent Task Steps", float(m.group(1)), "count")

    # Dedup
    dedup = []
    seen = set()
    for x in out:
        key = (x["metric_code"], x["metric_value"], x["metric_unit"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(x)
    return dedup

def fetch_recent_evidence(cur, company_id: int, limit: int):
    cur.execute("""
        SELECT
          ei.id AS evidence_item_id,
          ei.source_snapshot_id,
          ei.evidence_title,
          ei.evidence_text,
          ss.snapshot_time::date AS observation_date
        FROM evidence_item ei
        JOIN source_snapshot ss ON ss.id = ei.source_snapshot_id
        WHERE ei.company_id = %s
          AND ei.evidence_type IN ('body_extract', 'derived_body_extract')
        ORDER BY ei.id DESC
        LIMIT %s
    """, (company_id, limit))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def metric_exists(cur, company_id, source_snapshot_id, evidence_item_id, metric_code, metric_value, metric_unit):
    cur.execute("""
        SELECT 1
        FROM metric_observation
        WHERE company_id = %s
          AND source_snapshot_id = %s
          AND evidence_item_id = %s
          AND metric_code = %s
          AND metric_unit = %s
          AND ABS(metric_value - %s) < 0.000001
        LIMIT 1
    """, (company_id, source_snapshot_id, evidence_item_id, metric_code, metric_unit, metric_value))
    return cur.fetchone() is not None

def insert_metric(cur, company_id, source_snapshot_id, evidence_item_id, observation_date, metric):
    cur.execute("""
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
        metric["metric_code"],
        metric["metric_name"],
        metric["metric_value"],
        metric["metric_unit"],
        "point_in_time",
        observation_date,
        source_snapshot_id,
        evidence_item_id,
    ))
    return cur.fetchone()[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--company-name", required=True)
    ap.add_argument("--limit", type=int, default=120)
    args = ap.parse_args()

    conn = db_connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO insight, public")
                cur.execute("SELECT id, company_name FROM company WHERE lower(company_name) = lower(%s) LIMIT 1", (args.company_name,))
                row = cur.fetchone()
                if not row:
                    raise SystemExit(f"company not found: {args.company_name}")
                company_id = row[0]

                evidence_rows = fetch_recent_evidence(cur, company_id, args.limit)
                inserted = []
                scanned = 0

                for ev in evidence_rows:
                    scanned += 1
                    text = norm(ev.get("evidence_text"))
                    metrics = extract_metrics_from_text(text)
                    for metric in metrics:
                        exists = metric_exists(
                            cur,
                            company_id=company_id,
                            source_snapshot_id=ev["source_snapshot_id"],
                            evidence_item_id=ev["evidence_item_id"],
                            metric_code=metric["metric_code"],
                            metric_value=metric["metric_value"],
                            metric_unit=metric["metric_unit"],
                        )
                        if exists:
                            continue
                        metric_id = insert_metric(
                            cur,
                            company_id=company_id,
                            source_snapshot_id=ev["source_snapshot_id"],
                            evidence_item_id=ev["evidence_item_id"],
                            observation_date=ev["observation_date"] or date.today(),
                            metric=metric,
                        )
                        inserted.append({
                            "id": metric_id,
                            "metric_code": metric["metric_code"],
                            "metric_name": metric["metric_name"],
                            "metric_value": metric["metric_value"],
                            "metric_unit": metric["metric_unit"],
                            "source_snapshot_id": ev["source_snapshot_id"],
                            "evidence_item_id": ev["evidence_item_id"],
                            "evidence_title": ev["evidence_title"],
                        })

        print(json.dumps({
            "ok": True,
            "company_name": args.company_name,
            "scanned_evidence_count": scanned,
            "inserted_metric_count": len(inserted),
            "sample_inserted": inserted[:20],
        }, ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
