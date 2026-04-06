#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt as PPTPt
    HAS_PPTX = True
except Exception:
    HAS_PPTX = False

ROOT = Path(__file__).resolve().parents[2]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def ts_compact():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def slugify(value: str):
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", value or "").strip("-").lower()
    return s or "account-strategy"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def flatten_citations(case_data: dict):
    rows = []
    for entity_name, block in (case_data.get("db_backed_entities") or {}).items():
        for c in (block.get("recent_citations") or []):
            rows.append({
                "scope": "entity",
                "entity_name": entity_name,
                "claim_code": c.get("claim_code"),
                "citation_label": c.get("citation_label"),
                "citation_url": c.get("citation_url"),
                "citation_note": c.get("citation_note"),
                "evidence_item_id": c.get("evidence_item_id"),
                "source_snapshot_id": c.get("source_snapshot_id"),
                "source_id": c.get("source_id"),
            })

    for entity_name, block in (case_data.get("db_backed_competitors") or {}).items():
        for c in (block.get("recent_citations") or []):
            rows.append({
                "scope": "competitor",
                "entity_name": entity_name,
                "claim_code": c.get("claim_code"),
                "citation_label": c.get("citation_label"),
                "citation_url": c.get("citation_url"),
                "citation_note": c.get("citation_note"),
                "evidence_item_id": c.get("evidence_item_id"),
                "source_snapshot_id": c.get("source_snapshot_id"),
                "source_id": c.get("source_id"),
            })
    return rows

def write_docx(path: Path, case_data: dict, citations: list):
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)

    req = case_data.get("request") or {}
    case_code = req.get("case_code")
    partner = (req.get("partner") or {}).get("name")
    cloud = (req.get("cloud_vendor") or {}).get("name")

    doc.add_heading("ORIS Account Strategy Insight Report", level=0)
    p = doc.add_paragraph()
    p.add_run("Case Code: ").bold = True
    p.add_run(str(case_code))
    p = doc.add_paragraph()
    p.add_run("Theme: ").bold = True
    p.add_run(f"{partner} + {cloud} automotive joint account strategy")

    doc.add_heading("1. Executive Summary", level=1)
    for item in (case_data.get("recommendation_framework") or [])[:2]:
        doc.add_paragraph(item.get("title"), style="List Bullet")
        for point in (item.get("points") or [])[:3]:
            doc.add_paragraph(point, style="List Bullet 2")

    doc.add_heading("2. Core Entity Signal Summary", level=1)
    table = doc.add_table(rows=1, cols=5)
    hdr = table.rows[0].cells
    hdr[0].text = "Entity"
    hdr[1].text = "Signal Strength"
    hdr[2].text = "Snapshots"
    hdr[3].text = "Evidence"
    hdr[4].text = "Citations"
    for row in (case_data.get("entity_summaries") or []):
        cells = table.add_row().cells
        cells[0].text = str(row.get("entity_name"))
        cells[1].text = str(row.get("signal_strength"))
        cells[2].text = str(row.get("source_snapshot_count_recent"))
        cells[3].text = str(row.get("evidence_item_count_recent"))
        cells[4].text = str(row.get("citation_count_recent"))

    doc.add_heading("3. Competitor Benchmark", level=1)
    for row in (case_data.get("competitor_benchmark_ref", {}).get("comparison_matrix") or []):
        doc.add_paragraph(
            f"{row.get('entity_name')}: signal={row.get('signal_strength')}, "
            f"snapshots={row.get('source_snapshot_count_recent')}, "
            f"evidence={row.get('evidence_item_count_recent')}, "
            f"citations={row.get('citation_count_recent')}",
            style="List Bullet"
        )

    doc.add_heading("4. Recommendation Framework", level=1)
    for item in (case_data.get("recommendation_framework") or []):
        doc.add_paragraph(item.get("title"), style="List Bullet")
        for point in (item.get("points") or [])[:5]:
            doc.add_paragraph(point, style="List Bullet 2")

    doc.add_heading("5. Citation Appendix", level=1)
    for c in citations[:80]:
        doc.add_paragraph(
            f"[{c.get('entity_name')}] {c.get('citation_label')} | {c.get('citation_url')}",
            style="List Bullet"
        )

    doc.save(path)

def autosize_sheet(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            v = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(v))
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 60)

def write_sheet(ws, headers, rows):
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical="center")
    for row in rows:
        ws.append(row)
    autosize_sheet(ws)

def write_xlsx(path: Path, case_data: dict, citations: list):
    wb = Workbook()
    ws = wb.active
    ws.title = "Overview"

    req = case_data.get("request") or {}
    overview_rows = [
        ("case_code", req.get("case_code")),
        ("partner", (req.get("partner") or {}).get("name")),
        ("cloud_vendor", (req.get("cloud_vendor") or {}).get("name")),
        ("customer_count", len(req.get("customers") or [])),
        ("competitor_count", len(case_data.get("competitor_benchmark_ref", {}).get("comparison_matrix") or [])),
        ("generated_at", case_data.get("ts")),
    ]
    write_sheet(ws, ["field", "value"], overview_rows)

    ws2 = wb.create_sheet("Entity_Summaries")
    rows2 = []
    for x in (case_data.get("entity_summaries") or []):
        rows2.append([
            x.get("entity_name"),
            x.get("signal_strength"),
            x.get("source_snapshot_count_recent"),
            x.get("evidence_item_count_recent"),
            x.get("metric_observation_count_recent"),
            x.get("citation_count_recent"),
            " | ".join(x.get("sample_metric_codes") or [])
        ])
    write_sheet(
        ws2,
        ["entity_name", "signal_strength", "snapshots", "evidence", "metrics", "citations", "sample_metric_codes"],
        rows2
    )

    ws3 = wb.create_sheet("Competitor_Matrix")
    rows3 = []
    for x in (case_data.get("competitor_benchmark_ref", {}).get("comparison_matrix") or []):
        rows3.append([
            x.get("entity_name"),
            x.get("entity_type"),
            x.get("signal_strength"),
            x.get("source_snapshot_count_recent"),
            x.get("evidence_item_count_recent"),
            x.get("metric_observation_count_recent"),
            x.get("citation_count_recent"),
            " | ".join(x.get("dimensions") or [])
        ])
    write_sheet(
        ws3,
        ["entity_name", "entity_type", "signal_strength", "snapshots", "evidence", "metrics", "citations", "dimensions"],
        rows3
    )

    ws4 = wb.create_sheet("Recommendations")
    rows4 = []
    for item in (case_data.get("recommendation_framework") or []):
        if item.get("points"):
            for idx, point in enumerate(item.get("points") or [], start=1):
                rows4.append([item.get("title"), idx, point])
        else:
            rows4.append([item.get("title"), "", ""])
    write_sheet(ws4, ["recommendation_title", "point_no", "point"], rows4)

    ws5 = wb.create_sheet("Citations")
    rows5 = []
    for c in citations:
        rows5.append([
            c.get("scope"),
            c.get("entity_name"),
            c.get("claim_code"),
            c.get("citation_label"),
            c.get("citation_url"),
            c.get("citation_note"),
            c.get("evidence_item_id"),
            c.get("source_snapshot_id"),
            c.get("source_id")
        ])
    write_sheet(
        ws5,
        ["scope", "entity_name", "claim_code", "citation_label", "citation_url", "citation_note", "evidence_item_id", "source_snapshot_id", "source_id"],
        rows5
    )

    wb.save(path)

def add_bullets(slide, title, bullets):
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.clear()
    for i, bullet in enumerate(bullets):
        p = body.paragraphs[0] if i == 0 else body.add_paragraph()
        p.text = bullet
        p.level = 0
        if HAS_PPTX:
            p.font.size = PPTPt(20)

def write_pptx(path: Path, case_data: dict):
    prs = Presentation()

    req = case_data.get("request") or {}
    partner = (req.get("partner") or {}).get("name")
    cloud = (req.get("cloud_vendor") or {}).get("name")

    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "ORIS Account Strategy Briefing"
    slide.placeholders[1].text = f"{partner} + {cloud}\nAutomotive Joint AI Strategy"

    summary = next((x for x in (case_data.get("recommendation_framework") or []) if x.get("recommendation_code") == "joint_solution_fit"), None)
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    add_bullets(slide, "联合能力主张", summary.get("points") if summary else ["联合能力主张待补充"])

    for item in (case_data.get("recommendation_framework") or []):
        if str(item.get("recommendation_code", "")).startswith("customer-"):
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            add_bullets(slide, item.get("title"), item.get("points") or [])

    slide = prs.slides.add_slide(prs.slide_layouts[1])
    matrix = case_data.get("competitor_benchmark_ref", {}).get("comparison_matrix") or []
    bullets = [
        f"{x.get('entity_name')}: signal={x.get('signal_strength')}, evidence={x.get('evidence_item_count_recent')}, citations={x.get('citation_count_recent')}"
        for x in matrix[:6]
    ]
    add_bullets(slide, "欧洲竞争对手对标信号", bullets)

    slide = prs.slides.add_slide(prs.slide_layouts[1])
    add_bullets(
        slide,
        "下一步",
        [
            "将 account_strategy JSON 与 citation_link 接入正式报告生成。",
            "输出客户版 Word / Excel / PPT 正式材料。",
            "注册 report_artifact 并通过 Feishu 交付。"
        ]
    )

    prs.save(path)

def write_storyline_json(path: Path, case_data: dict):
    storyline = {
        "title": "ORIS Account Strategy Briefing",
        "slides": [
            {"title": "封面", "points": ["Akkodis + Huawei Cloud", "Automotive Joint AI Strategy"]},
            *[
                {"title": x.get("title"), "points": x.get("points") or []}
                for x in (case_data.get("recommendation_framework") or [])
            ]
        ]
    }
    save_json(path, storyline)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", required=True)
    args = ap.parse_args()

    req = json.loads(args.input_json)
    input_json_path = Path(req["input_json_path"])
    case_data = load_json(input_json_path)

    case_code = (case_data.get("request") or {}).get("case_code") or "account-strategy"
    out_dir = ROOT / "outputs" / "report_build" / slugify(case_code) / ts_compact()
    out_dir.mkdir(parents=True, exist_ok=True)

    citations = flatten_citations(case_data)

    docx_path = out_dir / "account_strategy_report.docx"
    xlsx_path = out_dir / "account_strategy_workbook.xlsx"
    json_path = out_dir / "account_strategy_bundle.json"

    write_docx(docx_path, case_data, citations)
    write_xlsx(xlsx_path, case_data, citations)
    save_json(json_path, case_data)

    artifact_plan = [
        {"artifact_type": "word", "path": str(docx_path.relative_to(ROOT))},
        {"artifact_type": "excel", "path": str(xlsx_path.relative_to(ROOT))},
        {"artifact_type": "json", "path": str(json_path.relative_to(ROOT))}
    ]

    ppt_status = "generated"
    if HAS_PPTX:
        pptx_path = out_dir / "account_strategy_deck.pptx"
        write_pptx(pptx_path, case_data)
        artifact_plan.append({"artifact_type": "ppt", "path": str(pptx_path.relative_to(ROOT))})
    else:
        ppt_status = "python_pptx_not_available_storyline_generated"
        storyline_path = out_dir / "account_strategy_deck_storyline.json"
        write_storyline_json(storyline_path, case_data)
        artifact_plan.append({"artifact_type": "ppt_storyline", "path": str(storyline_path.relative_to(ROOT))})

    out = {
        "ok": True,
        "skill_name": "report_build_skill.account_strategy_runner",
        "schema_version": "v1",
        "ts": utc_now(),
        "request": req,
        "conclusion": "account-strategy report bundle generated from ORIS account_strategy_case JSON.",
        "core_data": [
            {"field": "case_code", "value": case_code},
            {"field": "citation_count_total", "value": len(citations)},
            {"field": "ppt_status", "value": ppt_status},
            {"field": "generated_artifact_count", "value": len(artifact_plan)}
        ],
        "artifact_plan": artifact_plan
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
