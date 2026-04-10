#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREE_RESEARCH_UPGRADE_RULE_CFG_PATH = ROOT / "config" / "free_research_upgrade_rule_config.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def ts_compact():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def normalize(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)

def fmt_num(v, digits=1):
    try:
        x = float(v)
        if abs(x - int(x)) < 1e-9:
            return str(int(x))
        return f"{x:.{digits}f}"
    except Exception:
        return str(v)

def metric_display_line_cn(row: dict):
    code = normalize(row.get("metric_code"))
    name = normalize(row.get("metric_name") or code)
    value = row.get("metric_value")
    unit = normalize(row.get("metric_unit"))
    obs = normalize(row.get("observation_date"))

    if unit == "percent":
        value_txt = f"{fmt_num(value)}%"
    elif unit == "USD_billion":
        value_txt = f"{fmt_num(value)}亿美元"
    elif unit == "RMB_billion":
        value_txt = f"{fmt_num(value)}十亿元人民币"
    elif unit == "USD_million":
        try:
            value_txt = f"{float(value)/100:.1f}亿美元"
        except Exception:
            value_txt = f"{fmt_num(value)}百万美元"
    elif unit == "RMB_million":
        try:
            value_txt = f"{float(value)/100:.1f}亿元人民币"
        except Exception:
            value_txt = f"{fmt_num(value)}百万元人民币"
    elif unit == "million_accounts":
        value_txt = f"{fmt_num(value)}百万账户"
    elif unit == "billion_users":
        value_txt = f"{fmt_num(value)}十亿用户"
    else:
        value_txt = f"{fmt_num(value)}{unit}".strip()

    tail = f"（{obs}）" if obs else ""
    return f"{name}: {value_txt}{tail}".strip()

def metric_should_hide(row: dict):
    code = normalize(row.get("metric_code")).lower()
    unit = normalize(row.get("metric_unit"))
    try:
        value = float(row.get("metric_value"))
    except Exception:
        value = None

    if value is None:
        return True
    if code in {"official_source_snapshot_count", "extracted_evidence_segment_count"}:
        return True
    if code == "google_cloud_revenue" and unit == "USD_million" and value > 50000:
        return True
    if code == "google_services_revenue" and unit == "USD_million" and value > 500000:
        return True
    if code == "advertising_revenue_share" and not (0 <= value <= 100):
        return True
    if code.endswith("_yoy") and unit == "percent" and not (-100 <= value <= 1000):
        return True
    if code == "gemini_users" and not (0 < value <= 10):
        return True
    if code == "paid_subscriptions" and not (0 < value <= 5000):
        return True
    return False

def metric_priority_for_profile(focus_profile: str):
    if focus_profile == "internet_platform":
        return [
            "google_services_revenue",
            "google_services_revenue_yoy",
            "google_cloud_revenue",
            "google_cloud_revenue_yoy",
            "google_search_and_other_revenue",
            "advertising_revenue_share",
            "paid_subscriptions",
            "gemini_users",
            "revenue",
            "revenue_yoy",
            "gross_profit",
            "operating_profit",
            "net_profit",
            "free_cash_flow",
        ]
    if focus_profile == "foundation_model_company":
        return [
            "api_revenue",
            "enterprise_customer_count",
            "monthly_tokens",
            "benchmark_score",
            "agent_task_steps",
            "revenue",
            "revenue_yoy",
        ]
    if focus_profile == "automotive_oem":
        return [
            "vehicle_sales_total",
            "ev_sales",
            "revenue",
            "revenue_yoy",
            "gross_profit",
            "operating_profit",
            "net_profit",
            "free_cash_flow",
        ]
    return ["revenue", "revenue_yoy", "gross_profit", "operating_profit", "net_profit", "free_cash_flow"]

def rank_metric(row: dict, focus_profile: str):
    code = normalize(row.get("metric_code")).lower()
    unit = normalize(row.get("metric_unit"))
    try:
        value = float(row.get("metric_value"))
    except Exception:
        value = 0.0

    score = 0
    if unit in {"USD_billion", "RMB_billion", "percent", "million_accounts", "billion_users"}:
        score += 20
    elif unit in {"USD_million", "RMB_million"}:
        score += 10

    if code.endswith("_yoy") and unit == "percent":
        score += 6
    if code == "google_cloud_revenue" and unit == "USD_billion" and 0 < value < 500:
        score += 12
    if code == "google_services_revenue" and unit == "USD_billion" and 0 < value < 500:
        score += 12
    if code == "google_search_and_other_revenue" and unit == "USD_million" and 0 < value < 500000:
        score += 8
    return score

def top_numeric_kpis(profile: dict, focus_profile: str, limit: int = 8):
    priority = metric_priority_for_profile(focus_profile)
    rank = {x.lower(): i for i, x in enumerate(priority)}
    best_by_code = {}

    for row in profile.get("recent_metric_observations") or []:
        code = normalize(row.get("metric_code")).lower()
        if not code:
            continue
        if metric_should_hide(row):
            continue

        line = metric_display_line_cn(row)
        candidate = (
            rank.get(code, 9999),
            -rank_metric(row, focus_profile),
            line,
            normalize(row.get("observation_date")),
            normalize(row.get("source_snapshot_id")),
            normalize(row.get("evidence_item_id")),
        )
        old = best_by_code.get(code)
        if old is None or candidate < old:
            best_by_code[code] = candidate

    rows = sorted(best_by_code.values(), key=lambda x: (x[0], x[1], x[2], x[3], x[4], x[5]))
    return [x[2] for x in rows[:limit]]

def default_gap_findings(company_name: str, focus_profile: str):
    gaps = []
    if focus_profile == "internet_platform":
        gaps.append("互联网平台画像下，仍需持续补强收入、利润、广告、云、用户与订阅等核心经营指标的历年序列。")
    elif focus_profile == "foundation_model_company":
        gaps.append("基础模型公司画像下，仍需持续补强 API 商业化、企业客户、推理成本、基准成绩与 Agent 落地数据。")
    elif focus_profile == "automotive_oem":
        gaps.append("汽车画像下，仍需持续补强销量、ASP、毛利率、现金流、智驾能力与关键车型交付数据。")
    else:
        gaps.append(f"{company_name} 当前仍需继续补强高价值正文证据、结构化指标与历年序列。")
    gaps.append("应优先补充年报、季报、业绩会材料中的正文段落和表格，而不是导航页或订阅页。")
    return gaps

def followup_terms(company_name: str, focus_profile: str):
    if focus_profile == "internet_platform":
        return [
            f"{company_name} annual report revenue operating profit cash flow",
            f"{company_name} investor relations earnings presentation pdf",
            f"{company_name} advertising revenue cloud revenue paid subscriptions annual report",
            f"{company_name} operating margin segment revenue annual results",
        ]
    if focus_profile == "foundation_model_company":
        return [
            f"{company_name} api pricing enterprise customers benchmark agent",
            f"{company_name} token inference benchmark enterprise api",
            f"{company_name} annual report revenue operating profit cash flow",
        ]
    if focus_profile == "automotive_oem":
        return [
            f"{company_name} annual report deliveries revenue gross margin cash flow",
            f"{company_name} investor relations earnings presentation pdf",
            f"{company_name} adas takeover acceleration range annual report",
        ]
    return [
        f"{company_name} annual report revenue operating profit cash flow",
        f"{company_name} investor relations earnings presentation pdf",
    ]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json-path", required=True)
    ap.add_argument("--output-path", default=None)
    args = ap.parse_args()

    input_path = Path(args.input_json_path)
    data = load_json(input_path)

    profile = data.get("db_backed_profile") or data.get("company_profile") or {}
    company = (profile.get("company") or {})
    request = data.get("request") or {}

    company_name = company.get("company_name") or request.get("company_name") or "company"
    focus_profile = request.get("focus_profile") or data.get("focus_profile") or profile.get("focus_profile") or "generic_company"

    numeric_kpis = top_numeric_kpis(profile, focus_profile, limit=8)
    gap_findings = default_gap_findings(company_name, focus_profile)

    exec_summary = [
        f"{company_name} 当前已完成一版基于可得证据的{focus_profile}洞察，但仍需继续提高证据密度与量化深度。",
        "现阶段最核心短板不是写作层，而是源数据层：高价值正文、结构化指标、历年序列和可比口径仍需持续沉淀。",
    ]
    if numeric_kpis:
        exec_summary.append("现有可提炼量化信息包括：" + "；".join(numeric_kpis[:3]))
    exec_summary.append("下一步应优先修复：" + gap_findings[0])

    company_slug = f"company-profile-{company_name.lower().replace(' ', '-')}"
    output_path = Path(args.output_path) if args.output_path else (ROOT / "outputs" / "free_research_upgrade" / company_name.lower().replace(" ", "-") / f"{ts_compact()}.json")

    payload = {
        "company_slug": company_slug,
        "bundle_file": "",
        "upgrade_file": str(output_path.relative_to(ROOT)),
        "bundle_synthesis_mode": data.get("synthesis_mode") or "deterministic_fallback",
        "upgrade_used_mode": "deterministic_fallback",
        "upgrade_llm_ok": False,
        "exec_summary": exec_summary,
        "numeric_kpis": numeric_kpis,
        "gap_findings": gap_findings,
        "followup_search_terms": followup_terms(company_name, focus_profile),
        "upgrade_json": {
            "used_mode": "deterministic_fallback",
            "llm_ok": False,
            "exec_summary": exec_summary,
            "numeric_kpis": numeric_kpis,
            "gap_findings": gap_findings,
            "followup_search_terms": followup_terms(company_name, focus_profile),
        }
    }

    write_json(output_path, payload)

    print(json.dumps({
        "ok": True,
        "output_path": str(output_path.relative_to(ROOT)),
        "company_name": company_name,
        "focus_profile": focus_profile,
        "llm_ok": False,
        "used_mode": "deterministic_fallback",
        "has_upgrade_json": True
    }, ensure_ascii=False, indent=2))



# === CONFIG_DRIVEN_FREE_RESEARCH_UPGRADE_START ===
def load_free_research_upgrade_rule_cfg():
    try:
        return json.loads(FREE_RESEARCH_UPGRADE_RULE_CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "version": 1,
            "generic": {
                "max_numeric_kpis": 8,
                "max_gap_findings": 4,
                "max_followup_search_terms": 6,
                "summary_templates": {
                    "line_1": "{company_name} 当前已完成一版基于可得证据的{focus_label}洞察，但仍需继续提高证据密度与量化深度。",
                    "line_2": "现阶段最核心短板不是写作层，而是源数据层：高价值正文、结构化指标、历年序列和可比口径仍需持续沉淀。",
                    "line_3": "现有可提炼量化信息包括：{numeric_preview}",
                    "line_4": "下一步应优先修复：{primary_gap}"
                }
            },
            "focus_profile_display": {
                "generic_company": "通用公司"
            },
            "focus_profiles": {
                "generic_company": {
                    "default_gap_findings": [
                        "当前画像下，仍需继续补强收入、利润、现金流、核心产品与竞争定位等关键证据。"
                    ],
                    "followup_search_terms": [
                        "{company_name} annual report revenue operating profit cash flow"
                    ]
                }
            }
        }

def _fru_dedupe(items, limit=None):
    out = []
    seen = set()
    for x in items or []:
        s = str(x or "").strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if limit is not None and len(out) >= limit:
            break
    return out

def _fru_focus_label(focus_profile: str):
    cfg = load_free_research_upgrade_rule_cfg()
    labels = cfg.get("focus_profile_display") or {}
    return labels.get(focus_profile) or focus_profile or "通用公司"

def _fru_profile_cfg(focus_profile: str):
    cfg = load_free_research_upgrade_rule_cfg()
    profiles = cfg.get("focus_profiles") or {}
    return profiles.get(focus_profile) or profiles.get("generic_company") or {}

def _fru_generic_cfg():
    cfg = load_free_research_upgrade_rule_cfg()
    return cfg.get("generic") or {}

def _fru_apply_config_postprocess(data):
    if not isinstance(data, dict):
        return data

    used_mode = data.get("used_mode")
    llm_ok = data.get("llm_ok")

    if used_mode not in (None, "deterministic_fallback") and llm_ok is True:
        return data

    generic = _fru_generic_cfg()
    company_name = (
        data.get("company_name")
        or data.get("entity")
        or data.get("company")
        or "目标公司"
    )
    focus_profile = (
        data.get("focus_profile")
        or data.get("profile")
        or "generic_company"
    )
    focus_label = _fru_focus_label(focus_profile)
    prof_cfg = _fru_profile_cfg(focus_profile)

    max_numeric = int(generic.get("max_numeric_kpis", 8))
    max_gap = int(generic.get("max_gap_findings", 4))
    max_terms = int(generic.get("max_followup_search_terms", 6))

    numeric = _fru_dedupe(
        (data.get("numeric_kpis") or [])
        + (data.get("better_numeric_kpis") or []),
        limit=max_numeric
    )

    gap_findings = _fru_dedupe(
        (data.get("gap_findings") or [])
        + (prof_cfg.get("default_gap_findings") or []),
        limit=max_gap
    )

    followup_terms = []
    if data.get("followup_search_terms"):
        followup_terms.extend(data.get("followup_search_terms") or [])
    else:
        for term in (prof_cfg.get("followup_search_terms") or []):
            followup_terms.append(str(term).format(company_name=company_name))
    followup_terms = _fru_dedupe(followup_terms, limit=max_terms)

    tpl = generic.get("summary_templates") or {}
    exec_summary = [
        str(tpl.get("line_1", "{company_name} 当前已完成一版基于可得证据的{focus_label}洞察，但仍需继续提高证据密度与量化深度。")).format(
            company_name=company_name,
            focus_profile=focus_profile,
            focus_label=focus_label
        ),
        str(tpl.get("line_2", "现阶段最核心短板不是写作层，而是源数据层：高价值正文、结构化指标、历年序列和可比口径仍需持续沉淀。"))
    ]

    if numeric:
        exec_summary.append(
            str(tpl.get("line_3", "现有可提炼量化信息包括：{numeric_preview}")).format(
                numeric_preview="；".join(numeric[:3])
            )
        )
    if gap_findings:
        exec_summary.append(
            str(tpl.get("line_4", "下一步应优先修复：{primary_gap}")).format(
                primary_gap=gap_findings[0]
            )
        )

    exec_summary = _fru_dedupe(exec_summary, limit=4)

    data["company_name"] = company_name
    data["focus_profile"] = focus_profile
    data["used_mode"] = data.get("used_mode") or "deterministic_fallback"
    data["exec_summary"] = exec_summary
    data["better_exec_summary"] = exec_summary
    data["numeric_kpis"] = numeric
    data["gap_findings"] = gap_findings
    data["followup_search_terms"] = followup_terms
    data["postprocess_mode"] = "config_driven_deterministic_fallback"
    data["postprocess_config_path"] = str(FREE_RESEARCH_UPGRADE_RULE_CFG_PATH.relative_to(ROOT))
    return data

if "dump_json" in globals():
    _ORIG_dump_json = dump_json

    def dump_json(path, data):
        if isinstance(data, dict):
            data = _fru_apply_config_postprocess(data)
        return _ORIG_dump_json(path, data)
# === CONFIG_DRIVEN_FREE_RESEARCH_UPGRADE_END ===

if __name__ == "__main__":
    main()
