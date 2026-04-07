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

def build_synthesis(data: dict):
    profile = data.get("db_backed_profile") or {}
    prompt = {
        "task": "生成高质量公司洞察内容",
        "requirements": {
            "style": "专业、深入、分层",
            "must_cover": [
                "公司规模与覆盖区域",
                "主营业务与品牌结构",
                "核心产品与核心竞争力",
                "AI/智能化技术栈与产品方向",
                "行业位置与竞争态势",
                "风险与持续跟踪指标"
            ],
            "must_distinguish": ["事实", "推断", "建议", "风险"]
        },
        "input": {
            "request": data.get("request"),
            "core_data": data.get("core_data"),
            "facts": data.get("facts"),
            "inferences": data.get("inferences"),
            "risks": data.get("risks"),
            "recent_snapshots": profile.get("recent_snapshots"),
            "recent_evidence_items": profile.get("recent_evidence_items"),
            "recent_metric_observations": profile.get("recent_metric_observations")
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
            if parsed:
                return {"mode": "llm", "sections": parsed}
    except Exception:
        pass

    sections = {
        "executive_summary": [
            data.get("conclusion") or "公司洞察已生成。",
            "建议把公司介绍从官网文案提升为：业务结构、技术方向、全球布局、竞争位置、风险与跟踪指标五层。"
        ],
        "company_view": data.get("facts") or [],
        "technology_view": data.get("inferences") or [],
        "industry_view": [
            "公司洞察不应停留在官网口径，后续需叠加行业、竞争与客户视角形成完整判断。"
        ],
        "risk_view": data.get("risks") or [],
        "tracking_kpis": data.get("next_steps") or []
    }
    return {"mode": "deterministic_fallback", "sections": sections}

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
    company = ((data.get("db_backed_profile") or {}).get("company") or {})
    title = doc.add_heading(f"{company.get('company_name') or data['request'].get('company_name')} 公司洞察报告", 0)
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
    for row in ((data.get("db_backed_profile") or {}).get("recent_evidence_items") or [])[:30]:
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

    profile = data.get("db_backed_profile") or {}

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
    company = ((data.get("db_backed_profile") or {}).get("company") or {})
    company_name = company.get("company_name") or data.get("request", {}).get("company_name") or "company"

    synth = build_synthesis(data)
    sections = synth["sections"]

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
        "schema_version": "v2",
        "ts": utc_now(),
        "request": {
            "analysis_type": "company_profile",
            "input_json_path": args.input_json_path,
            "company_name": company_name
        },
        "conclusion": "rich company_profile bundle generated from DB-backed company_profile output.",
        "synthesis_mode": synth.get("mode"),
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
