BACKFILL_KIND = "foundation_model_metric_backfill"
#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from datetime import date

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
    return {
        "host": db["host"],
        "port": db["port"],
        "dbname": db["dbname"],
        "user": db["user"],
        "password": db.get("password", ""),
    }

def db_connect():
    return psycopg2.connect(**load_db_cfg())

def set_search_path(cur):
    try:
        cur.execute("SET search_path TO insight, public")
    except Exception:
        pass

def find_company(cur, company_name: str):
    cur.execute("""
        SELECT id, company_name
        FROM company
        WHERE company_name = %s
           OR company_name ILIKE %s
        ORDER BY id DESC
        LIMIT 1
    """, (company_name, f"%{company_name}%"))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"company not found: {company_name}")
    return {"id": row[0], "company_name": row[1]}

def fetch_evidence(cur, company_id: int):
    cur.execute("""
        SELECT
            e.id AS evidence_item_id,
            e.source_snapshot_id,
            COALESCE(e.evidence_title, '') AS evidence_title,
            COALESCE(e.evidence_text, '') AS evidence_text,
            COALESCE(e.evidence_date::date, ss.snapshot_time::date, CURRENT_DATE) AS obs_date
        FROM evidence_item e
        LEFT JOIN source_snapshot ss ON ss.id = e.source_snapshot_id
        WHERE e.company_id = %s
        ORDER BY e.id DESC
        LIMIT 500
    """, (company_id,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def metric_exists(cur, company_id: int, evidence_item_id: int, metric_code: str):
    cur.execute("""
        SELECT 1
        FROM metric_observation
        WHERE company_id = %s
          AND evidence_item_id = %s
          AND metric_code = %s
        LIMIT 1
    """, (company_id, evidence_item_id, metric_code))
    return cur.fetchone() is not None

def insert_metric(cur, company_id: int, row: dict, metric_code: str, metric_name: str, metric_value: float, metric_unit: str):
    if metric_exists(cur, company_id, row["evidence_item_id"], metric_code):
        return None
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
        metric_code,
        metric_name,
        float(metric_value),
        metric_unit,
        "point_in_time",
        row["obs_date"] or date.today(),
        row["source_snapshot_id"],
        row["evidence_item_id"],
    ))
    return cur.fetchone()[0]

def norm(text: str) -> str:
    s = str(text or "")
    s = s.replace("\x00", " ").replace("\ufeff", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def add_hit(hits, company_id, row, metric_code, metric_name, metric_value, metric_unit):
    hits.append({
        "company_id": company_id,
        "row": row,
        "metric_code": metric_code,
        "metric_name": metric_name,
        "metric_value": float(metric_value),
        "metric_unit": metric_unit,
    })

def parse_model_pricing_line(text: str):
    out = []
    lines = re.split(r"[\n\r]+|(?<=\|)\s*(?=GLM-)|(?<=\.)\s+(?=GLM-)", text)
    for line in lines:
        s = norm(line)
        if "GLM-" not in s:
            continue

        m = re.search(
            r"(GLM-[A-Za-z0-9\.\-]+)\s*\|\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*\|\s*\$?\s*([0-9]+(?:\.[0-9]+)?)?.*?\|\s*\$?\s*([0-9]+(?:\.[0-9]+)?)",
            s,
            flags=re.I
        )
        if not m:
            continue

        model = m.group(1).lower().replace(".", "_").replace("-", "_")
        input_price = float(m.group(2))
        output_price = float(m.group(4))
        out.append((f"{model}_input_price", f"{m.group(1)} Input Price", input_price, "USD_per_1M_tokens"))
        out.append((f"{model}_output_price", f"{m.group(1)} Output Price", output_price, "USD_per_1M_tokens"))
    return out

def collect_metrics(company_id: int, rows: list[dict]):
    hits = []
    for row in rows:
        title = norm(row["evidence_title"])
        text = norm(row["evidence_text"])
        joined = f"{title} {text}".strip()
        lower = joined.lower()

        for metric_code, metric_name, metric_value, metric_unit in parse_model_pricing_line(joined):
            add_hit(hits, company_id, row, metric_code, metric_name, metric_value, metric_unit)

        m = re.search(r"(?:超过|over)\s*([0-9]+)\s*步", joined, flags=re.I)
        if m:
            add_hit(hits, company_id, row, "agent_long_horizon_steps", "Agent Long Horizon Steps", float(m.group(1)), "steps")

        m = re.search(r"([0-9]+)\s*B-class", joined, flags=re.I)
        if m:
            add_hit(hits, company_id, row, "model_class_size", "Model Class Size", float(m.group(1)), "B_params_class")

        m = re.search(r"half a billion users|([0-9]+(?:\.[0-9]+)?)\s*billion users", lower, flags=re.I)
        if m:
            value = 0.5 if "half a billion users" in lower else float(m.group(1))
            add_hit(hits, company_id, row, "model_users", "Model Users", value, "billion_users")

        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*元/百万tokens", joined, flags=re.I)
        if m and ("价格" in joined or "计费" in joined):
            add_hit(hits, company_id, row, "knowledge_service_price", "Knowledge Service Price", float(m.group(1)), "CNY_per_1M_tokens")

        m = re.search(r"音频[:：]\s*([0-9]+(?:\.[0-9]+)?)\s*元/分钟", joined)
        if m:
            add_hit(hits, company_id, row, "realtime_audio_price", "Realtime Audio Price", float(m.group(1)), "CNY_per_minute")

        m = re.search(r"视频[:：]\s*([0-9]+(?:\.[0-9]+)?)\s*元/分钟", joined)
        if m:
            add_hit(hits, company_id, row, "realtime_video_price", "Realtime Video Price", float(m.group(1)), "CNY_per_minute")

    dedup = {}
    for h in hits:
        key = (h["row"]["evidence_item_id"], h["metric_code"])
        old = dedup.get(key)
        candidate = (
            str(h["row"]["obs_date"]),
            -(h["row"]["source_snapshot_id"] or 0),
            h["metric_value"]
        )
        if old is None or candidate < old["sort_key"]:
            x = dict(h)
            x["sort_key"] = candidate
            dedup[key] = x
    return list(dedup.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--company-name", required=True)
    args = ap.parse_args()

    conn = db_connect()
    inserted = []
    try:
        with conn:
            with conn.cursor() as cur:
                set_search_path(cur)
                company = find_company(cur, args.company_name)
                rows = fetch_evidence(cur, company["id"])
                hits = collect_metrics(company["id"], rows)

                for h in hits:
                    metric_id = insert_metric(
                        cur,
                        company_id=h["company_id"],
                        row=h["row"],
                        metric_code=h["metric_code"],
                        metric_name=h["metric_name"],
                        metric_value=h["metric_value"],
                        metric_unit=h["metric_unit"],
                    )
                    if metric_id is not None:
                        inserted.append({
                            "id": metric_id,
                            "metric_code": h["metric_code"],
                            "metric_name": h["metric_name"],
                            "metric_value": h["metric_value"],
                            "metric_unit": h["metric_unit"],
                            "source_snapshot_id": h["row"]["source_snapshot_id"],
                            "evidence_item_id": h["row"]["evidence_item_id"],
                            "evidence_title": h["row"]["evidence_title"],
                        })

        print(json.dumps({
            "ok": True,
            "company_name": args.company_name,
            "scanned_evidence_count": len(rows),
            "inserted_metric_count": len(inserted),
            "sample_inserted": inserted[:20]
        }, ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
