#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook
from pptx import Presentation

import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.oris_llm_client import call_oris_text

ROOT = Path(__file__).resolve().parents[2]
QUALITY_CFG_PATH = ROOT / "config" / "company_profile_quality.json"
FOCUS_PROFILE_PATH = ROOT / "config" / "company_focus_profiles.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def ts_compact():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def normalize(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)

def safe_json_from_text(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    import re
    m = re.search(r'(\{.*\})', text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None
    return None

def load_quality_cfg():
    try:
        return load_json(QUALITY_CFG_PATH)
    except Exception:
        return {}

def load_focus_profiles():
    try:
        return load_json(FOCUS_PROFILE_PATH)
    except Exception:
        return {"default_profile": "generic_company", "profiles": {}}

def pick_focus_profile(data: dict):
    req = data.get("request") or {}
    profile = (
        req.get("focus_profile")
        or data.get("focus_profile")
        or ((data.get("company_profile") or {}).get("focus_profile"))
        or ((data.get("db_backed_profile") or {}).get("focus_profile"))
    )
    if profile:
        return profile
    cfg = load_focus_profiles()
    return cfg.get("default_profile") or "generic_company"

def unified_profile(data: dict):
    profile = data.get("company_profile") or {}
    if profile:
        return profile
    profile = data.get("db_backed_profile") or {}
    if profile:
        return profile
    return {
        "company": {
            "company_name": (data.get("request") or {}).get("company_name")
        },
        "recent_snapshots": data.get("recent_snapshots") or [],
        "recent_evidence_items": data.get("recent_evidence_items") or [],
        "recent_metric_observations": data.get("recent_metric_observations") or []
    }

def pick_company_name(data: dict, profile: dict):
    company = (profile.get("company") or {})
    return (
        company.get("company_name")
        or (data.get("request") or {}).get("company_name")
        or "company"
    )

def flatten_text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return "\n".join([x for x in [flatten_text(i) for i in v] if x]).strip()
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            t = flatten_text(val)
            if t:
                parts.append(f"{k}: {t}")
        return "\n".join(parts).strip()
    return str(v)

def score_text(text: str, focus_profile: str, cfg: dict):
    import re
    t = (text or "").strip()
    if not t:
        return -999
    tl = t.lower()
    score = 0

    if re.search(r"\d", t):
        score += 2
    if "%" in t:
        score += 2
    if re.search(r"(€|\$|¥|亿元|万台|million|billion|bn|mn)", t, flags=re.I):
        score += 2

    for kw in (cfg.get("finance_keywords") or []):
        if kw and kw.lower() in tl:
            score += 1

    prof_keywords = ((cfg.get("profile_keywords") or {}).get(focus_profile) or [])
    for kw in prof_keywords:
        if kw and kw.lower() in tl:
            score += 2

    for noise in (cfg.get("noise_patterns") or []):
        if noise and noise.lower() in tl:
            score -= 4

    if len(t) >= int(cfg.get("min_text_length", 35)):
        score += 1
    if len(t) > int(cfg.get("max_text_length", 320)):
        score -= 1

    return score

def top_evidence_items(profile: dict, focus_profile: str, cfg: dict, limit: int = 8):
    rows = []
    for row in profile.get("recent_evidence_items") or []:
        text = flatten_text(row.get("evidence_text") or "")
        title = flatten_text(row.get("evidence_title") or "")
        joined = f"{title}\n{text}".strip()
        if not joined:
            continue
        sc = score_text(joined, focus_profile, cfg)
        rows.append((sc, title, text))
    rows.sort(key=lambda x: (-x[0], -(len(x[2]) if x[2] else 0)))
    out = []
    for sc, title, text in rows[:limit]:
        body = text if len(text) <= 320 else text[:320] + "..."
        title = clean_evidence_label(title)
        body = clean_evidence_label(body)
        joined = f"{title}：{body}" if title else body
        if not is_user_facing_noise(joined, cfg):
            out.append(joined)
    return out

def top_metric_items(profile: dict, focus_profile: str, cfg: dict, limit: int = 8):
    rows = []
    blocklist = set(cfg.get("metric_blocklist") or [])
    for row in profile.get("recent_metric_observations") or []:
        code = normalize(row.get("metric_code"))
        if code in blocklist:
            continue
        name = normalize(row.get("metric_name"))
        value = normalize(row.get("metric_value"))
        unit = normalize(row.get("metric_unit"))
        obs = normalize(row.get("observation_date"))
        if not name and not code:
            continue
        text = f"{name or code}: {value}{unit} ({obs})".strip()
        sc = score_text(text, focus_profile, cfg) + 1
        rows.append((sc, text))
    rows.sort(key=lambda x: (-x[0], -len(x[1])))
    return [x[1] for x in rows[:limit]]

def profile_hint(focus_profile: str, cfg_profiles: dict):
    profiles = cfg_profiles.get("profiles") or {}
    prof = profiles.get(focus_profile) or {}
    label = prof.get("label") or focus_profile
    sections = prof.get("recommended_sections") or []
    req_metrics = prof.get("required_metric_codes") or []
    return {
        "profile_label": label,
        "recommended_sections": sections,
        "required_metric_codes": req_metrics
    }


def clean_evidence_label(text: str):
    import re
    t = normalize(text).strip()
    t = re.sub(r"\s*/\s*(derived|segment)\s*\d+\s*[:：]\s*", "：", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def is_internal_diagnostic_text(text: str):
    t = normalize(text).strip().lower()
    if not t:
        return True
    patterns = [
        "db-backed profile ready",
        "company row found in insight.company",
        "recent analysis_run count",
        "recent source_snapshot count",
        "recent evidence_item count",
        "recent metric_observation count",
        "company_profile_skill",
        "profile view:",
    ]
    return any(p in t for p in patterns)

def is_user_facing_noise(text: str, cfg: dict):
    t = normalize(text).strip()
    if not t:
        return True
    tl = t.lower()

    noise_patterns = [
        "investor alert options",
        "at least one of the checkboxes needs to be selected",
        "checkbox",
        "email address",
        "unsubscribe",
        "cookie",
        "cookies",
        "privacy",
        "newsletter",
        "accept all",
        "manage cookies",
        "opens in new window",
        "view all",
        "skip to content",
        "back to top",
    ]
    for p in noise_patterns:
        if p in tl:
            return True

    for p in (cfg.get("noise_patterns") or []):
        if p and p.lower() in tl:
            return True

    return False

def filter_user_facing_items(items, cfg: dict, max_items: int = 8):
    out = []
    seen = set()
    for item in items or []:
        t = normalize(item).strip()
        if not t:
            continue
        if is_internal_diagnostic_text(t):
            continue
        if is_user_facing_noise(t, cfg):
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= max_items:
            break
    return out

def bucket_evidence_items(items, focus_profile: str):
    company, tech, industry, risk = [], [], [], []

    tech_kws = [
        "ai", "模型", "model", "agent", "api", "云", "cloud", "platform",
        "mb.os", "software-defined", "adas", "automated driving",
        "token", "推理", "训练", "open platform", "maas"
    ]
    industry_kws = [
        "market", "competition", "competitive", "industry", "ecosystem",
        "advertising", "games", "payment", "fintech", "cloud revenue",
        "市场", "竞争", "行业", "生态", "广告", "游戏", "支付"
    ]
    risk_kws = [
        "risk", "risks", "uncertainty", "challenge", "pressure", "regulation",
        "headwind", "decline", "slower", "volatile",
        "风险", "不确定", "挑战", "压力", "监管", "下滑", "波动"
    ]

    if focus_profile == "automotive_oem":
        tech_kws += ["electric", "vans", "xev", "range", "800v", "智驾", "电动车", "车型"]
    elif focus_profile == "internet_platform":
        industry_kws += ["mau", "ecosystem", "social", "ad", "广告", "用户", "社交"]
    elif focus_profile == "foundation_model_company":
        tech_kws += ["glm", "reasoning", "inference", "foundation model", "大模型", "推理"]

    for item in items or []:
        tl = item.lower()
        if any(k.lower() in tl for k in risk_kws):
            risk.append(item)
        elif any(k.lower() in tl for k in tech_kws):
            tech.append(item)
        elif any(k.lower() in tl for k in industry_kws):
            industry.append(item)
        else:
            company.append(item)

    return company, tech, industry, risk

def merge_unique(*groups, limit: int = 8):
    out = []
    seen = set()
    for group in groups:
        for item in group or []:
            t = normalize(item).strip()
            if not t:
                continue
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
            if len(out) >= limit:
                return out
    return out

def build_synthesis(data: dict):
    profile = unified_profile(data)
    focus_profile = pick_focus_profile(data)
    cfg = load_quality_cfg()
    cfg_profiles = load_focus_profiles()
    hint = profile_hint(focus_profile, cfg_profiles)

    evidence_items = profile.get("recent_evidence_items") or []
    metric_items = profile.get("recent_metric_observations") or []

    prompt = {
        "task": "生成高质量公司洞察内容",
        "requirements": {
            "style": "专业、深入、分层、偏证据优先",
            "must_cover": [
                "公司规模与覆盖区域",
                "主营业务与品牌结构",
                "核心产品与核心竞争力",
                "AI/智能化技术栈与产品方向",
                "行业位置与竞争态势",
                "风险与持续跟踪指标"
            ],
            "must_distinguish": ["事实", "推断", "建议", "风险"],
            "chat_first": True
        },
        "focus_profile": focus_profile,
        "profile_hint": hint,
        "input": {
            "request": data.get("request"),
            "core_data": data.get("core_data"),
            "facts": data.get("facts"),
            "inferences": data.get("inferences"),
            "risks": data.get("risks"),
            "next_steps": data.get("next_steps"),
            "recent_snapshots": profile.get("recent_snapshots"),
            "recent_evidence_items": evidence_items[:20],
            "recent_metric_observations": metric_items[:20]
        },
        "output_schema": {
            "executive_summary": ["..."],
            "company_view": ["..."],
            "technology_view": ["..."],
            "industry_view": ["..."],
            "risk_view": ["..."],
            "tracking_kpis": ["..."]
        }
    }

    try:
        resp = call_oris_text(
            "请基于下面JSON生成严格JSON，不要输出解释文字：\n" + json.dumps(prompt, ensure_ascii=False),
            role="free_fallback",
            timeout_seconds=180
        )
        if resp.get("ok"):
            parsed = safe_json_from_text(resp.get("text", ""))
            if parsed and isinstance(parsed, dict):
                return {"mode": "llm", "sections": parsed, "focus_profile": focus_profile}
    except Exception:
        pass

    evidence_top = top_evidence_items(profile, focus_profile, cfg, limit=int(cfg.get("max_evidence_items", 8)))
    metrics_top = top_metric_items(profile, focus_profile, cfg, limit=int(cfg.get("max_metric_items", 8)))

    clean_facts = filter_user_facing_items(data.get("facts") or [], cfg, max_items=8)
    clean_inferences = filter_user_facing_items(data.get("inferences") or [], cfg, max_items=8)
    clean_risks = filter_user_facing_items(data.get("risks") or [], cfg, max_items=8)
    clean_next_steps = filter_user_facing_items(data.get("next_steps") or [], cfg, max_items=8)

    ev_company, ev_tech, ev_industry, ev_risk = bucket_evidence_items(evidence_top, focus_profile)

    summary = [
        data.get("conclusion") or "公司洞察已生成。",
        f"当前焦点画像：{hint['profile_label']}。",
        "建议以业务结构、核心产品/技术、竞争位置、风险与跟踪指标五层持续跟踪。"
    ]
    if metrics_top:
        summary.append("优先关注指标：" + "；".join(metrics_top[:3]))

    sections = {
        "executive_summary": merge_unique(summary, limit=4),
        "company_view": merge_unique(clean_facts, ev_company, limit=8),
        "technology_view": merge_unique(clean_inferences, ev_tech, limit=8),
        "industry_view": merge_unique(
            ["公司洞察不应停留在官网口径，需叠加行业、竞争、客户与资本市场视角形成完整判断。"],
            ev_industry,
            [f"建议重点展开的章节：{', '.join(hint['recommended_sections']) if hint['recommended_sections'] else 'company_positioning, business_model, risks, tracking_metrics'}。"],
            limit=8
        ),
        "risk_view": merge_unique(clean_risks, ev_risk, limit=8),
        "tracking_kpis": merge_unique(clean_next_steps, metrics_top, limit=8)
    }
    return {"mode": "deterministic_fallback", "sections": sections, "focus_profile": focus_profile}

def add_bullets(slide, title, items):
    slide.shapes.title.text = title
    tf = slide.placeholders[1].text_frame
    tf.clear()
    items = items or ["N/A"]
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = str(item)

def make_docx(path: Path, data: dict, sections: dict):
    doc = Document()
    profile = unified_profile(data)
    company_name = pick_company_name(data, profile)
    title = doc.add_heading(f"{company_name} 公司洞察报告", 0)
    title.runs[0].font.size = Pt(20)

    for name, title_text in [
        ("executive_summary", "执行摘要"),
        ("company_view", "公司层"),
        ("technology_view", "技术层"),
        ("industry_view", "行业层"),
        ("risk_view", "风险层"),
        ("tracking_kpis", "持续跟踪指标")
    ]:
        doc.add_heading(title_text, level=1)
        for item in sections.get(name) or []:
            doc.add_paragraph(str(item), style="List Bullet")

    doc.add_heading("原始证据", level=1)
    for row in (profile.get("recent_evidence_items") or [])[:30]:
        doc.add_paragraph(
            f"{normalize(row.get('evidence_title'))}\n{normalize(row.get('evidence_text'))}",
            style="List Bullet"
        )

    doc.save(path)

def make_xlsx(path: Path, data: dict):
    wb = Workbook()

    ws = wb.active
    ws.title = "core_data"
    ws.append(["field", "value"])
    for row in data.get("core_data") or []:
        ws.append([normalize(row.get("field")), normalize(row.get("value"))])

    ws2 = wb.create_sheet("sources")
    ws2.append(["source_name", "source_type", "url", "official_flag"])
    for row in data.get("sources") or []:
        ws2.append([
            normalize(row.get("source_name")),
            normalize(row.get("source_type")),
            normalize(row.get("url")),
            normalize(row.get("official_flag"))
        ])

    profile = unified_profile(data)

    ws3 = wb.create_sheet("evidence_raw")
    ws3.append(["id", "source_snapshot_id", "evidence_type", "evidence_title", "evidence_text", "evidence_date", "confidence_score"])
    for row in profile.get("recent_evidence_items") or []:
        ws3.append([
            normalize(row.get("id")),
            normalize(row.get("source_snapshot_id")),
            normalize(row.get("evidence_type")),
            normalize(row.get("evidence_title")),
            normalize(row.get("evidence_text")),
            normalize(row.get("evidence_date")),
            normalize(row.get("confidence_score"))
        ])

    ws4 = wb.create_sheet("metrics_raw")
    ws4.append(["id", "metric_code", "metric_name", "metric_value", "metric_unit", "observation_date", "source_snapshot_id"])
    for row in profile.get("recent_metric_observations") or []:
        ws4.append([
            normalize(row.get("id")),
            normalize(row.get("metric_code")),
            normalize(row.get("metric_name")),
            normalize(row.get("metric_value")),
            normalize(row.get("metric_unit")),
            normalize(row.get("observation_date")),
            normalize(row.get("source_snapshot_id"))
        ])

    wb.save(path)

def make_pptx(path: Path, sections: dict, company_name: str):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    add_bullets(slide, f"{company_name} 公司洞察", sections.get("executive_summary"))
    for title, key in [
        ("公司层", "company_view"),
        ("技术层", "technology_view"),
        ("行业层", "industry_view"),
        ("风险层", "risk_view"),
        ("持续跟踪指标", "tracking_kpis")
    ]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        add_bullets(slide, title, sections.get(key))
    prs.save(path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json-path", required=True)
    args = ap.parse_args()

    data = load_json(Path(args.input_json_path))
    profile = unified_profile(data)
    company_name = pick_company_name(data, profile)

    synth = build_synthesis(data)
    sections = synth["sections"]
    focus_profile = synth.get("focus_profile") or pick_focus_profile(data)

    slug = company_name.lower().replace(" ", "-")
    out_dir = ROOT / "outputs" / "report_build" / f"company-profile-{slug}" / ts_compact()
    out_dir.mkdir(parents=True, exist_ok=True)

    docx_path = out_dir / "company_profile_report.docx"
    xlsx_path = out_dir / "company_profile_workbook.xlsx"
    pptx_path = out_dir / "company_profile_deck.pptx"
    json_path = out_dir / "company_profile_bundle.json"

    make_docx(docx_path, data, sections)
    make_xlsx(xlsx_path, data)
    make_pptx(pptx_path, sections, company_name)

    bundle = {
        "ok": True,
        "skill_name": "report_build_skill.company_profile_bundle_runner",
        "schema_version": "v3",
        "ts": utc_now(),
        "request": {
            "analysis_type": "company_profile",
            "input_json_path": args.input_json_path,
            "company_name": company_name,
            "focus_profile": focus_profile
        },
        "focus_profile": focus_profile,
        "conclusion": "evidence-backed company_profile bundle generated from unified company profile input.",
        "synthesis_mode": synth.get("mode"),
        "sections": sections,
        "artifact_plan": [
            {"artifact_type": "word", "path": str(docx_path.relative_to(ROOT))},
            {"artifact_type": "excel", "path": str(xlsx_path.relative_to(ROOT))},
            {"artifact_type": "ppt", "path": str(pptx_path.relative_to(ROOT))},
            {"artifact_type": "json", "path": str(json_path.relative_to(ROOT))}
        ]
    }

    write_json(json_path, bundle)
    print(json.dumps(bundle, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
