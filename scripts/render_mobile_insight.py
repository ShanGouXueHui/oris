#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY_PATH = ROOT / "config" / "company_profile_quality.json"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_quality():
    return load_json(QUALITY_PATH)

def normalize_text(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def split_segments(text: str):
    raw = re.split(r'[\n\r]+|(?<=[\.\!\?。！？:])\s+', text or "")
    out = []
    seen = set()
    for seg in raw:
        s = normalize_text(seg)
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out

def is_noise(text: str, cfg: dict):
    t = (text or "").lower()
    for p in cfg.get("noise_patterns") or []:
        if p.lower() in t:
            return True
    return False

def score_text(text: str, focus_profile: str, cfg: dict):
    s = normalize_text(text)
    if not s:
        return -999

    score = 0
    low = s.lower()

    if len(s) < int(cfg.get("min_text_length", 35)):
        score -= 2
    if len(s) > int(cfg.get("max_text_length", 320)):
        score -= 1

    if is_noise(s, cfg):
        score -= 6

    if re.search(r'\d', s):
        score += 2

    for p in cfg.get("numeric_patterns") or []:
        if p.lower() in low:
            score += 2

    for kw in cfg.get("finance_keywords") or []:
        if kw.lower() in low:
            score += 2

    prof_keywords = ((cfg.get("profile_keywords") or {}).get(focus_profile) or [])
    for kw in prof_keywords:
        if kw.lower() in low:
            score += 2

    if re.search(r'(revenue|ebit|free cash flow|gross profit|unit sales|dividend|share buyback|ros|roe|guidance)', low):
        score += 3

    if re.search(r'(mb\.os|software-defined vehicle|robotaxi|automated driving|adas|g-class|cla|glc)', low):
        score += 3

    if re.search(r'(cookies|privacy|unsubscribe|email alert|contact sales|publisher:|source_type:|captured_at:|title:|url:)', low):
        score -= 8

    return score

def pick_high_value_segments(profile: dict, focus_profile: str, cfg: dict):
    snaps = (profile.get("recent_snapshots") or [])
    candidates = []

    for snap in snaps:
        parsed_rel = snap.get("parsed_text_storage_path") or ""
        if not parsed_rel:
            continue
        parsed_path = ROOT / parsed_rel
        if not parsed_path.exists():
            continue

        try:
            text = parsed_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        title = snap.get("snapshot_title") or snap.get("source_name") or "source"
        url = snap.get("snapshot_url") or ""

        for seg in split_segments(text):
            sc = score_text(seg, focus_profile, cfg)
            if sc < int(cfg.get("min_score", 4)):
                continue
            candidates.append({
                "score": sc,
                "title": title,
                "url": url,
                "text": seg,
                "source_type": snap.get("source_type") or snap.get("snapshot_type") or ""
            })

    dedup = []
    seen = set()
    for row in sorted(candidates, key=lambda x: (-x["score"], -len(x["text"]))):
        key = normalize_text(row["text"]).lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)

    if dedup:
        return dedup

    # fallback to evidence rows when parsed snapshots do not yield good正文
    evs = profile.get("recent_evidence_items") or []
    fallback = []
    for row in evs:
        seg = normalize_text(row.get("evidence_text") or "")
        sc = score_text(seg, focus_profile, cfg)
        if sc < int(cfg.get("min_score", 4)):
            continue
        fallback.append({
            "score": sc,
            "title": row.get("evidence_title") or "evidence",
            "url": "",
            "text": seg,
            "source_type": row.get("evidence_type") or ""
        })

    dedup2 = []
    seen2 = set()
    for row in sorted(fallback, key=lambda x: (-x["score"], -len(x["text"]))):
        key = normalize_text(row["text"]).lower()
        if key in seen2:
            continue
        seen2.add(key)
        dedup2.append(row)
    return dedup2

def pick_metrics(profile: dict, cfg: dict):
    rows = profile.get("recent_metric_observations") or []
    block = set(cfg.get("metric_blocklist") or [])
    out = []
    seen = set()

    for row in rows:
        code = row.get("metric_code")
        if code in block:
            continue
        key = (row.get("metric_name"), row.get("observation_date"), row.get("metric_value"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)

    return out[: int(cfg.get("max_metric_items", 8))]

def profile_hint(focus_profile: str):
    mapping = {
        "automotive_oem": "结合官方来源与投资者关系材料，重点应看：收入结构、利润质量、销量与车型结构、软件/智驾/电动化能力、竞争地位与跟踪指标。",
        "internet_platform": "结合官方来源与投资者关系材料，重点应看：收入结构、广告/游戏/云/支付等业务贡献、利润质量、AI 商业化与竞争位置。",
        "foundation_model_company": "结合官方来源与官方平台材料，重点应看：模型/Agent/API 商业模式、产品矩阵、生态扩展、研发与商业化平衡。"
    }
    return mapping.get(focus_profile, "结合官方来源与投资者关系材料，重点应看：收入结构、利润质量、核心产品能力、竞争地位与未来跟踪指标。")

def render_markdown(data: dict):
    cfg = load_quality()
    profile = data.get("db_backed_profile") or {}
    company = profile.get("company") or {}
    entity = company.get("company_name") or data.get("request", {}).get("company_name") or "公司"
    focus_profile = data.get("request", {}).get("focus_profile") or data.get("focus_profile") or "generic_company"

    high_value = pick_high_value_segments(profile, focus_profile, cfg)
    metrics = pick_metrics(profile, cfg)
    snaps = profile.get("recent_snapshots") or []
    evs = profile.get("recent_evidence_items") or []

    lines = []
    lines.append(f"# {entity} 公司洞察")
    lines.append("")
    lines.append("## 一、执行摘要")
    if high_value:
        for row in high_value[: int(cfg.get("max_summary_items", 4))]:
            lines.append(f"- {row['text']}")
    else:
        lines.append("- 当前高价值正文证据不足，结论可信度受限。")
    lines.append("")
    lines.append("## 二、公司定位与商业模式")
    lines.append(f"- 当前识别的分析类型：{data.get('request', {}).get('analysis_type', 'company_profile')}；焦点画像：{focus_profile}。")
    lines.append(f"- {profile_hint(focus_profile)}")
    lines.append("")

    lines.append("## 三、核心证据摘录")
    if high_value:
        for i, row in enumerate(high_value[: int(cfg.get('max_evidence_items', 8))], 1):
            lines.append(f"- {i}. {row['title']}：{row['text']}")
    else:
        lines.append("- 暂无可用正文证据。")
    lines.append("")

    lines.append("## 四、指标摘录")
    if metrics:
        for row in metrics:
            lines.append(
                f"- {row.get('metric_name')}: {row.get('metric_value')} {row.get('metric_unit') or ''} ({row.get('observation_date')})"
            )
    else:
        lines.append("- 当前无高价值结构化指标。")
    lines.append("")

    lines.append("## 五、风险与边界")
    if not high_value:
        lines.append("- 当前高价值正文证据不足，部分结论仍需补充财报、业绩会或监管文件验证。")
    lines.append("- 当前版本优先基于官方来源直读结果，若官方页面壳层噪音较重，部分结论仍需人工复核。")
    lines.append("- 对正式高层汇报或投资判断，仍建议继续补充财报、业绩会、监管文件与可比公司数据。")
    lines.append("")

    lines.append("## 六、数据来源链接")
    seen = set()
    for row in snaps:
        url = row.get("snapshot_url") or ""
        if url and url not in seen:
            seen.add(url)
            lines.append(f"- {url}")

    markdown = "\n".join(lines).strip()
    return {
        "ok": True,
        "blocked": False,
        "entity": entity,
        "focus_profile": focus_profile,
        "snapshot_count": len(snaps),
        "evidence_count": len(evs),
        "metric_count": len(profile.get("recent_metric_observations") or []),
        "high_value_evidence_count": len(high_value),
        "markdown": markdown,
        "preview": markdown[:2000]
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json-path", default=None)
    ap.add_argument("--source-json-path", default=None)
    ap.add_argument("--profile-json-path", default=None)
    ap.add_argument("--compiled-case-path", default=None)
    args = ap.parse_args()

    if not args.input_json_path and args.profile_json_path:
        args.input_json_path = args.profile_json_path
    if not args.source_json_path and args.profile_json_path:
        args.source_json_path = args.profile_json_path

    input_path = args.input_json_path or args.source_json_path
    if not input_path:
        raise SystemExit("missing --input-json-path or --source-json-path")

    data = load_json(Path(input_path))
    out = render_markdown(data)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
