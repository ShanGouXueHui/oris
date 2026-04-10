#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "company_focus_config.json"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def normalize_text(s: str) -> str:
    return (s or "").strip()

def find_first_alias(text: str, aliases: dict):
    hits = []
    for canonical, alias_list in aliases.items():
        for alias in alias_list:
            if re.search(r'[\u4e00-\u9fff]', alias):
                idx = text.find(alias)
                if idx >= 0:
                    hits.append((idx, canonical, alias))
            else:
                m = re.search(r'(?<![A-Za-z0-9_])' + re.escape(alias) + r'(?![A-Za-z0-9_])', text, flags=re.IGNORECASE)
                if m:
                    hits.append((m.start(), canonical, alias))
    if not hits:
        return None
    hits.sort(key=lambda x: x[0])
    return {
        "position": hits[0][0],
        "canonical": hits[0][1],
        "matched_alias": hits[0][2]
    }

def collect_competitors(text: str, aliases: dict, focus_company: str):
    found = []
    for canonical, alias_list in aliases.items():
        if canonical == focus_company:
            continue
        for alias in alias_list:
            if re.search(r'[\u4e00-\u9fff]', alias):
                if alias in text:
                    found.append(canonical)
                    break
            else:
                if re.search(r'(?<![A-Za-z0-9_])' + re.escape(alias) + r'(?![A-Za-z0-9_])', text, flags=re.IGNORECASE):
                    found.append(canonical)
                    break
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return out

def collect_topics(text: str, generic_terms: list[str]):
    found = []
    lower_text = text.lower()
    for term in generic_terms:
        if term.lower() in lower_text:
            found.append(term)
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return out

def build_sanitized_prompt(raw_prompt: str, focus_company: str, competitors: list[str], topics: list[str]) -> str:
    parts = []
    parts.append(f"唯一目标公司：{focus_company}")
    parts.append("约束：除目标公司外，其他名称仅作为竞品、场景或分析维度，不允许作为主体公司绑定。")
    parts.append("约束：禁止把 AI Agent、Workflow Automation、Integration Platform、Developer Tooling 这类行业概念识别为公司主体。")
    parts.append("")
    parts.append(f"请仅围绕公司【{focus_company}】输出一份适合手机直接阅读的公司洞察。")
    parts.append("输出重点：公司定位、核心产品能力、商业模式、竞争优势、能力边界、潜在短板、适配客户、商务合作建议。")

    if competitors:
        parts.append("补充要求：请参考以下竞品进行比较，但不要把它们当作主体公司：")
        parts.append("、".join(competitors))

    if topics:
        parts.append("补充维度：以下术语仅为分析维度，不是主体公司：")
        parts.append("、".join(topics))

    parts.append("")
    parts.append("用户原始需求如下：")
    parts.append(raw_prompt.strip())

    return "\n".join(parts).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-text", required=True)
    args = ap.parse_args()

    cfg = load_json(CONFIG_PATH)
    raw_prompt = normalize_text(args.prompt_text)

    focus = find_first_alias(raw_prompt, cfg["company_aliases"])
    if not focus:
        print(json.dumps({
            "ok": False,
            "focus_company": None,
            "sanitized_prompt": "",
            "reason": "focus_company_not_found"
        }, ensure_ascii=False))
        return

    focus_company = focus["canonical"]
    competitors = collect_competitors(raw_prompt, cfg["company_aliases"], focus_company)
    topics = collect_topics(raw_prompt, cfg["generic_terms"])
    sanitized_prompt = build_sanitized_prompt(raw_prompt, focus_company, competitors, topics)

    print(json.dumps({
        "ok": True,
        "focus_company": focus_company,
        "matched_alias": focus["matched_alias"],
        "competitors": competitors,
        "topics": topics,
        "sanitized_prompt": sanitized_prompt
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
