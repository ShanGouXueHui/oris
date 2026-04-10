#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
import re

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.insight_db import db_connect, set_search_path
from lib.insight_skill_runtime import build_standard_output, load_request

SKILL_NAME = "company_profile_skill"
QUALITY_CFG_PATH = ROOT / "config" / "company_profile_quality.json"

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


def is_low_value_evidence_row(row: dict):
    text = str((row or {}).get("evidence_text") or "").strip().lower()
    title = str((row or {}).get("evidence_title") or "").strip().lower()
    bad_prefixes = [
        "title:",
        "url:",
        "publisher:",
        "source_type:",
        "captured_at:",
        "fetch_error:",
        "content_type:",
        "final_url:"
    ]
    noise_terms = [
        "cookie",
        "cookies",
        "privacy policy",
        "accept cookies",
        "analytics cookies",
        "email alert",
        "unsubscribe",
        "copyright ©",
        "all rights reserved",
        "订阅邮件提醒",
        "隐私政策",
        "just a moment",
        "checking your browser",
        "enable javascript and cookies",
        "skip to main content",
        "investor alert options",
        "email address required",
        "selecting a year value will change the accordion list",
        "news (includes earnings date announcements",
        "upcoming conference appearances",
        "your information will be processed",
        "form required accessibility fix"
    ]

    if not text:
        return True
    for x in bad_prefixes:
        if text.startswith(x):
            return True
    for x in noise_terms:
        if x in text:
            return True
    if "segment" in title and len(text) < 40:
        return True
    return False


def pick_high_value_evidence_rows(rows):
    rows = rows or []
    filtered = [r for r in rows if not is_low_value_evidence_row(r)]

    def sort_key(r):
        text = str(r.get("evidence_text") or "")
        evidence_type = str(r.get("evidence_type") or "")
        score = 0
        if evidence_type == "body_extract":
            score += 4
        if any(x in text.lower() for x in ["revenue", "sales", "deliver", "margin", "profit", "cash flow", "收入", "销量", "交付", "利润", "毛利率", "现金流"]):
            score += 3
        if any(ch.isdigit() for ch in text):
            score += 2
        score += min(len(text) // 120, 3)
        conf = float(r.get("confidence_score") or 0)
        return (-score, -conf, -(int(r.get("id") or 0)))

    ranked = sorted(filtered, key=sort_key)
    if ranked:
        return ranked[:20]
    return rows[:20]

def load_quality_cfg():
    try:
        return json.loads(QUALITY_CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"generic": {}, "focus_profiles": {}}

def read_text_safe(path_str):
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def normalize_blob(text: str) -> str:
    s = str(text or "")
    s = s.replace("\x00", " ").replace("\ufeff", " ")
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def split_candidate_segments(text: str):
    raw = normalize_blob(text)
    if not raw:
        return []
    blocks = []
    for seg in re.split(r"\n\s*\n", raw):
        seg = normalize_blob(seg)
        if seg:
            blocks.append(seg)
    if not blocks:
        blocks = [normalize_blob(x) for x in re.split(r"(?<=[。！？!?\.])\s+", raw) if normalize_blob(x)]
    return blocks

def score_segment(seg: str, snapshot_type: str, focus_profile: str, cfg: dict):
    generic = (cfg.get("generic") or {})
    fp = ((cfg.get("focus_profiles") or {}).get(focus_profile) or {})
    noise = [str(x).lower() for x in (generic.get("noise_substrings") or [])]
    lower = seg.lower()

    if any(x in lower for x in noise):
        return -999

    if len(seg) < int(generic.get("min_segment_length", 60)):
        return -999
    if len(seg) > int(generic.get("max_segment_length", 1200)):
        return -999

    score = 0
    if any(ch.isdigit() for ch in seg):
        score += 3

    for pat in (generic.get("prefer_numeric_regex") or []):
        try:
            if re.search(pat, seg, flags=re.I):
                score += 2
        except Exception:
            pass

    for kw in (fp.get("keywords") or []):
        if str(kw).lower() in lower:
            score += 2

    if snapshot_type in ("annual_report", "investor_relations"):
        score += 2
    elif snapshot_type in ("official_website", "product_page"):
        score += 1

    if len(seg) >= 120:
        score += 1

    return score

def build_derived_evidence(snapshots, focus_profile: str, company_id):
    cfg = load_quality_cfg()
    generic = (cfg.get("generic") or {})
    max_per_source = int(generic.get("max_segments_per_source", 4))
    max_total = int(generic.get("max_segments_total", 18))

    out = []
    seen = set()

    for snap in snapshots or []:
        snapshot_type = snap.get("source_type") or snap.get("snapshot_type") or ""
        text = read_text_safe(snap.get("parsed_text_storage_path"))
        if not text:
            continue

        scored = []
        for seg in split_candidate_segments(text):
            score = score_segment(seg, snapshot_type, focus_profile, cfg)
            if score < 1:
                continue
            key = seg[:200]
            if key in seen:
                continue
            seen.add(key)
            scored.append((score, seg))

        scored.sort(key=lambda x: (-x[0], -len(x[1])))
        for idx, (_, seg) in enumerate(scored[:max_per_source], 1):
            out.append({
                "id": f"derived-{snap.get('id')}-{idx}",
                "source_snapshot_id": snap.get("id"),
                "company_id": company_id,
                "evidence_type": "derived_body_extract",
                "evidence_title": f"{snap.get('snapshot_title') or snap.get('source_name') or 'Source'} / derived {idx:02d}",
                "evidence_text": seg,
                "evidence_number": None,
                "evidence_unit": None,
                "evidence_date": None,
                "confidence_score": 0.85
            })

    out = out[:max_total]
    return out


# === V4_QUALITY_HELPERS_START ===
def load_quality_cfg():
    import json
    cfg_path = ROOT / "config" / "company_profile_quality.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {"generic": {}, "focus_profiles": {}}

def read_text_safe(path_str):
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def normalize_blob(text: str) -> str:
    import re
    s = str(text or "")
    s = s.replace("\x00", " ").replace("\ufeff", " ")
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def split_candidate_segments(text: str):
    import re
    raw = normalize_blob(text)
    if not raw:
        return []
    blocks = []
    for seg in re.split(r"\n\s*\n", raw):
        seg = normalize_blob(seg)
        if seg:
            blocks.append(seg)
    if not blocks:
        blocks = [normalize_blob(x) for x in re.split(r"(?<=[。！？!?\.])\s+", raw) if normalize_blob(x)]
    return blocks

def is_metadata_like_segment(seg: str) -> bool:
    s = normalize_blob(seg)
    lower = s.lower()

    bad_prefixes = (
        "title:",
        "url:",
        "source_type:",
        "publisher:",
        "captured_at:",
        "fetch_error:",
        "status_code:",
        "content_type:",
        "final_url:",
        "root_domain:"
    )
    if lower.startswith(bad_prefixes):
        return True

    if len(s) < 80 and s.count(":") >= 2:
        return True

    meta_tokens = [
        "privacy",
        "cookies",
        "copyright",
        "all rights reserved",
        "email alert",
        "unsubscribe",
        "accept cookies",
        "terms of use"
    ]
    hit = sum(1 for x in meta_tokens if x in lower)
    if hit >= 2:
        return True

    return False

def score_segment(seg: str, snapshot_type: str, focus_profile: str, cfg: dict):
    import re
    generic = (cfg.get("generic") or {})
    fp = ((cfg.get("focus_profiles") or {}).get(focus_profile) or {})
    noise = [str(x).lower() for x in (generic.get("noise_substrings") or [])]
    lower = seg.lower()

    if is_metadata_like_segment(seg):
        return -999

    if any(x in lower for x in noise):
        return -999

    if len(seg) < int(generic.get("min_segment_length", 60)):
        return -999
    if len(seg) > int(generic.get("max_segment_length", 1200)):
        return -999

    score = 0
    has_digit = any(ch.isdigit() for ch in seg)
    if has_digit:
        score += 3

    regex_hits = 0
    for pat in (generic.get("prefer_numeric_regex") or []):
        try:
            if re.search(pat, seg, flags=re.I):
                regex_hits += 1
        except Exception:
            pass
    score += min(regex_hits, 3) * 2

    keyword_hits = 0
    for kw in (fp.get("keywords") or []):
        if str(kw).lower() in lower:
            keyword_hits += 1
    score += min(keyword_hits, 4) * 2

    if snapshot_type in ("annual_report", "investor_relations"):
        score += 2
    elif snapshot_type in ("official_website", "product_page"):
        score += 1

    if len(seg) >= 120:
        score += 1

    if (not has_digit) and keyword_hits < 2 and len(seg) < 160:
        return -999

    return score

def build_derived_evidence(snapshots, focus_profile: str, company_id):
    cfg = load_quality_cfg()
    generic = (cfg.get("generic") or {})
    max_per_source = int(generic.get("max_segments_per_source", 4))
    max_total = int(generic.get("max_segments_total", 18))

    out = []
    seen = set()

    for snap in snapshots or []:
        snapshot_type = snap.get("source_type") or snap.get("snapshot_type") or ""
        text = read_text_safe(snap.get("parsed_text_storage_path"))
        if not text:
            continue

        scored = []
        for seg in split_candidate_segments(text):
            score = score_segment(seg, snapshot_type, focus_profile, cfg)
            if score < 4:
                continue
            key = seg[:240]
            if key in seen:
                continue
            seen.add(key)
            scored.append((score, seg))

        scored.sort(key=lambda x: (-x[0], -len(x[1])))
        for idx, (_, seg) in enumerate(scored[:max_per_source], 1):
            out.append({
                "id": f"derived-{snap.get('id')}-{idx}",
                "source_snapshot_id": snap.get("id"),
                "company_id": company_id,
                "evidence_type": "derived_body_extract",
                "evidence_title": f"{snap.get('snapshot_title') or snap.get('source_name') or 'Source'} / derived {idx:02d}",
                "evidence_text": seg,
                "evidence_number": None,
                "evidence_unit": None,
                "evidence_date": None,
                "confidence_score": 0.85
            })

    return out[:max_total]
# === V4_QUALITY_HELPERS_END ===

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
                    LIMIT 80
                    """,
                    (company_id,),
                )
                evidence_rows = pick_high_value_evidence_rows(evidence_rows)

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

                raw_evidence_rows = list(evidence_rows)

                latest_snapshot_ids = []
                for row in snapshots[:8]:
                    sid = row.get("id")
                    if sid is not None:
                        latest_snapshot_ids.append(sid)

                latest_clean_evidence_rows = pick_high_value_evidence_rows([
                    r for r in evidence_rows
                    if r.get("source_snapshot_id") in latest_snapshot_ids
                ])

                all_clean_evidence_rows = pick_high_value_evidence_rows(evidence_rows)

                if latest_clean_evidence_rows:
                    evidence_rows = latest_clean_evidence_rows
                else:
                    evidence_rows = all_clean_evidence_rows

                if not evidence_rows:
                    evidence_rows = []

                focus_profile = request.get("focus_profile") or "generic_company"
                raw_evidence_rows = list(evidence_rows)
                derived_evidence_rows = build_derived_evidence(snapshots, focus_profile, company_id)
                if derived_evidence_rows:
                    evidence_rows = derived_evidence_rows

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
                    {"field": "derived_evidence_item_count_recent", "value": len(derived_evidence_rows)},
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
                    "raw_evidence_items": raw_evidence_rows,
                    "recent_metric_observations": metric_rows,
                }

                print(json.dumps(json_safe(out), ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
