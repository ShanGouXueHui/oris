#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "chat_md"

URL_RE = re.compile(r'https?://[^\s<>"\')]+')

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))

def collect_urls(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                for m in URL_RE.findall(v):
                    out.append(m)
            collect_urls(v, out)
    elif isinstance(obj, list):
        for x in obj:
            collect_urls(x, out)
    elif isinstance(obj, str):
        for m in URL_RE.findall(obj):
            out.append(m)

def first_nonempty(*vals):
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def flatten_text(v):
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        parts = [flatten_text(x) for x in v]
        parts = [x for x in parts if x]
        return "\n".join(parts)
    if isinstance(v, dict):
        parts = []
        for kk, vv in v.items():
            t = flatten_text(vv)
            if t:
                parts.append(f"- {kk}: {t}")
        return "\n".join(parts)
    return ""

def get_by_keys(obj, keys):
    vals = []
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in keys:
                    vals.append(v)
                walk(v)
        elif isinstance(x, list):
            for y in x:
                walk(y)
    walk(obj)
    return vals

def best_section(bundle, keys, fallback=""):
    vals = get_by_keys(bundle, keys)
    texts = []
    for v in vals:
        t = flatten_text(v)
        if t:
            texts.append(t)
    if texts:
        return "\n\n".join(texts[:3]).strip()
    return fallback.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-json-path", required=True)
    ap.add_argument("--compiled-case-path", required=True)
    args = ap.parse_args()

    bundle = load_json(Path(args.bundle_json_path))
    compiled = load_json(Path(args.compiled_case_path))

    case_code = compiled.get("case_code") or "unknown_case"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{case_code}.md"

    title = first_nonempty(
        compiled.get("title"),
        (compiled.get("request") or {}).get("title"),
        case_code
    )

    questions = compiled.get("questions") or []
    entities = compiled.get("detected_entities") or []
    entity_names = [x.get("name") for x in entities if isinstance(x, dict) and x.get("name")]

    exec_summary = best_section(
        bundle,
        {"executive_summary", "summary", "overview", "conclusion", "key_messages"},
        fallback="本次输出已完成重新洞察与结构化整理，建议优先关注联合价值主张、行业竞争格局、技术栈适配、客户场景匹配与下一步落地动作。"
    )
    industry_comp = best_section(
        bundle,
        {"industry_view", "competition_view", "benchmark", "industry_and_competition", "market_landscape"},
        fallback=""
    )
    tech_stack = best_section(
        bundle,
        {"technology_view", "technology_stack_breakdown", "core_technology", "ai_capability", "tech_stack"},
        fallback=""
    )
    customer_scene = best_section(
        bundle,
        {"customer_view", "customer_strategy", "customer_scenario_analysis", "scenarios", "use_cases"},
        fallback=""
    )
    reco = best_section(
        bundle,
        {"joint_solution_or_recommendation", "recommendations", "next_steps", "action_plan"},
        fallback=""
    )
    risks = best_section(
        bundle,
        {"risks", "risks_and_next_steps", "risk", "constraints"},
        fallback=""
    )

    urls = []
    collect_urls(bundle, urls)
    collect_urls(compiled, urls)

    dedup = []
    seen = set()
    for u in urls:
        if u not in seen:
            dedup.append(u)
            seen.add(u)

    lines = []
    lines.append(f"# {title}")
    lines.append("")
    if entity_names:
        lines.append(f"**涉及主体：** {' / '.join(entity_names)}")
        lines.append("")
    lines.append("## 一、执行摘要")
    lines.append(exec_summary or "暂无可提炼摘要。")
    lines.append("")

    if questions:
        lines.append("## 二、本次重点问题")
        for q in questions:
            lines.append(f"- {q}")
        lines.append("")

    if industry_comp:
        lines.append("## 三、行业与竞争")
        lines.append(industry_comp)
        lines.append("")

    if tech_stack:
        lines.append("## 四、技术栈与能力拆解")
        lines.append(tech_stack)
        lines.append("")

    if customer_scene:
        lines.append("## 五、客户场景与落地机会")
        lines.append(customer_scene)
        lines.append("")

    if reco:
        lines.append("## 六、建议动作")
        lines.append(reco)
        lines.append("")

    if risks:
        lines.append("## 七、风险提示")
        lines.append(risks)
        lines.append("")

    lines.append("## 八、数据来源链接")
    if dedup:
        for u in dedup[:20]:
            lines.append(f"- {u}")
    else:
        lines.append("- 暂未抽取到结构化来源链接，请回看 evidence / citation bundle。")
    lines.append("")

    text = "\n".join(lines).strip() + "\n"
    out_path.write_text(text, encoding="utf-8")

    print_json({
        "ok": True,
        "output_path": str(out_path.relative_to(ROOT)),
        "source_link_count": min(len(dedup), 20),
        "preview": text[:800]
    })

if __name__ == "__main__":
    main()
