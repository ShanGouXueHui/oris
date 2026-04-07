#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.lib.oris_llm_client import call_oris_text
except Exception:
    call_oris_text = None

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _detect_deliverables(base_case: dict):
    vals = base_case.get("deliverables") or base_case.get("required_artifacts") or []
    out = []
    for x in vals:
        s = str(x).strip().lower()
        if s in ["word", "excel", "ppt", "pptx"]:
            out.append("ppt" if s == "pptx" else s)
    return sorted(set(out))

def _detect_analysis_type(base_case: dict):
    return (
        base_case.get("analysis_type")
        or ((base_case.get("request") or {}).get("analysis_type"))
        or "generic_insight"
    )

def _extract_json_maybe(text: str):
    if not isinstance(text, str) or not text.strip():
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'(\{.*\})', text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None
    return None

def _safe_llm_compare(prompt_text: str, base_case: dict, runtime_cfg: dict):
    if not runtime_cfg.get("enable_llm_shadow_compare"):
        return {"ok": False, "mode": "disabled", "error": "llm_shadow_compare_disabled"}

    if call_oris_text is None:
        return {"ok": False, "mode": "unavailable", "error": "oris_llm_client_not_importable"}

    system_prompt = """
你是 ORIS 的 compiler shadow reviewer。
你的任务不是重新生成最终报告，而是审查当前 compiler 结果，指出：
1. 缺失的分析维度
2. 缺失的结构章节
3. 缺失的实体/竞争对手/客户/技术栈
4. Word / Excel / PPT 各自应补充的内容
5. 哪些结论需要更多权威证据
请输出 JSON:
{
  "missing_dimensions": [],
  "missing_entities": [],
  "word_upgrades": [],
  "excel_upgrades": [],
  "ppt_upgrades": [],
  "quality_risks": [],
  "recommended_external_skills": []
}
""".strip()

    user_prompt = json.dumps({
        "prompt_text": prompt_text,
        "analysis_type": _detect_analysis_type(base_case),
        "deliverables": _detect_deliverables(base_case),
        "role_bindings": base_case.get("role_bindings"),
        "questions": base_case.get("questions"),
        "report_sections": base_case.get("report_sections"),
        "ppt_sections": base_case.get("ppt_sections"),
        "dimensions": base_case.get("dimensions")
    }, ensure_ascii=False)

    attempts = [
        {"system_prompt": system_prompt, "user_prompt": user_prompt},
        {"system": system_prompt, "user": user_prompt},
        {"prompt": system_prompt + "\n\n" + user_prompt}
    ]

    last_error = None
    for kwargs in attempts:
        try:
            raw = call_oris_text(**kwargs)
            if isinstance(raw, dict):
                parsed = raw
                raw_text = json.dumps(raw, ensure_ascii=False)
            else:
                raw_text = str(raw)
                parsed = _extract_json_maybe(raw_text) or {}
            return {
                "ok": True,
                "mode": "executed",
                "raw_text": raw_text[:12000],
                "parsed": parsed
            }
        except TypeError as e:
            last_error = f"type_error: {e}"
            continue
        except Exception as e:
            last_error = str(e)
            break

    return {"ok": False, "mode": "failed", "error": last_error or "unknown_error"}


def _norm_text_list(vals):
    out = []
    for x in vals or []:
        s = str(x).strip()
        if s:
            out.append(s)
    return out

def _deterministic_audit(base_case: dict, runtime_cfg: dict):
    report_sections = [str(x).strip() for x in (base_case.get("report_sections") or []) if str(x).strip()]
    ppt_sections = [str(x).strip() for x in (base_case.get("ppt_sections") or []) if str(x).strip()]
    deliverables = _detect_deliverables(base_case)

    required_word = runtime_cfg.get("word_requirements") or []
    required_excel = runtime_cfg.get("excel_requirements") or []
    required_ppt = runtime_cfg.get("ppt_requirements") or []

    missing_word = []
    missing_excel = []
    missing_ppt = []
    quality_risks = []

    if "word" in deliverables:
        existing = set(report_sections)
        for item in required_word:
            if item not in existing:
                missing_word.append(item)

    if "excel" in deliverables:
        # excel requirements are not explicit sections in compiled_case today,
        # so keep them as deterministic upgrade candidates
        missing_excel.extend(required_excel)

    if "ppt" in deliverables:
        existing = set(ppt_sections)
        for item in required_ppt:
            if item not in existing:
                missing_ppt.append(item)

    if not (base_case.get("dimensions") or []):
        quality_risks.append("缺少明确分析维度，后续报告容易泛化。")

    bindings = base_case.get("role_bindings") or {}
    if base_case.get("analysis_type") == "account_strategy":
        if not bindings.get("partner"):
            quality_risks.append("缺少 partner 绑定。")
        if not bindings.get("cloud_vendor"):
            quality_risks.append("缺少 cloud_vendor 绑定。")
        if not (bindings.get("customers") or []):
            quality_risks.append("缺少 customer 绑定。")
        if not (bindings.get("competitors") or []):
            quality_risks.append("缺少 competitor 绑定。")

    if base_case.get("analysis_type") == "company_profile":
        if not bindings.get("target_company"):
            quality_risks.append("缺少 target_company 绑定。")

    return {
        "word_upgrades": missing_word,
        "excel_upgrades": missing_excel,
        "ppt_upgrades": missing_ppt,
        "quality_risks": quality_risks
    }

def _pick_external_skills(base_case: dict, registry_cfg: dict, llm_compare: dict):
    deliverables = _detect_deliverables(base_case)
    analysis_type = _detect_analysis_type(base_case)
    items = registry_cfg.get("external_skills") or []

    wanted_categories = {"research_ingest", "llm_gateway"}
    if "word" in deliverables:
        wanted_categories.add("word_generation")
    if "ppt" in deliverables:
        wanted_categories.add("ppt_generation")

    picks = []
    for item in items:
        if item.get("category") not in wanted_categories:
            continue
        picks.append({
            "skill_code": item.get("skill_code"),
            "category": item.get("category"),
            "status": item.get("status"),
            "enabled": item.get("enabled"),
            "repo": item.get("repo"),
            "integration_mode": item.get("integration_mode"),
            "why": item.get("why"),
            "selected_for": analysis_type
        })

    llm_rec = ((llm_compare or {}).get("parsed") or {}).get("recommended_external_skills") or []
    llm_rec_norm = {str(x).strip().lower() for x in llm_rec if str(x).strip()}

    for item in picks:
        item["llm_recommended"] = item["skill_code"].strip().lower() in llm_rec_norm

    return picks

def build_compare_bundle(prompt_text: str, base_case: dict, runtime_cfg: dict, registry_cfg: dict):
    llm_compare = _safe_llm_compare(prompt_text, base_case, runtime_cfg)
    parsed = (llm_compare or {}).get("parsed") or {}
    deterministic = _deterministic_audit(base_case, runtime_cfg)

    merged_missing_dimensions = _norm_text_list(parsed.get("missing_dimensions"))
    merged_missing_entities = _norm_text_list(parsed.get("missing_entities"))
    merged_word_upgrades = _norm_text_list((parsed.get("word_upgrades") or []) + (deterministic.get("word_upgrades") or []))
    merged_excel_upgrades = _norm_text_list((parsed.get("excel_upgrades") or []) + (deterministic.get("excel_upgrades") or []))
    merged_ppt_upgrades = _norm_text_list((parsed.get("ppt_upgrades") or []) + (deterministic.get("ppt_upgrades") or []))
    merged_quality_risks = _norm_text_list((parsed.get("quality_risks") or []) + (deterministic.get("quality_risks") or []))

    external_skill_candidates = _pick_external_skills(base_case, registry_cfg, llm_compare)

    compare_summary = {
        "analysis_type": _detect_analysis_type(base_case),
        "deliverables": _detect_deliverables(base_case),
        "missing_dimensions_count": len(merged_missing_dimensions),
        "missing_entities_count": len(merged_missing_entities),
        "word_upgrade_count": len(merged_word_upgrades),
        "excel_upgrade_count": len(merged_excel_upgrades),
        "ppt_upgrade_count": len(merged_ppt_upgrades),
        "quality_risk_count": len(merged_quality_risks),
        "external_skill_candidate_count": len(external_skill_candidates)
    }

    evolution_actions = []
    for x in merged_missing_dimensions:
        evolution_actions.append({"action_type": "add_dimension_candidate", "value": x, "source": "merged_compare"})
    for x in merged_missing_entities:
        evolution_actions.append({"action_type": "add_entity_candidate", "value": x, "source": "merged_compare"})
    for x in merged_word_upgrades:
        evolution_actions.append({"action_type": "upgrade_word_structure_candidate", "value": x, "source": "merged_compare"})
    for x in merged_excel_upgrades:
        evolution_actions.append({"action_type": "upgrade_excel_evidence_candidate", "value": x, "source": "merged_compare"})
    for x in merged_ppt_upgrades:
        evolution_actions.append({"action_type": "upgrade_ppt_story_candidate", "value": x, "source": "merged_compare"})
    for x in merged_quality_risks:
        evolution_actions.append({"action_type": "quality_risk_flag", "value": x, "source": "merged_compare"})

    return {
        "parser_mode": "hybrid_compare_plus_external_shadow",
        "execution_mode": "deterministic_plus_llm_compare_plus_skill_registry",
        "trace_appends": [
            "external_ai_compare",
            "compare_summary",
            "external_skill_benchmark",
            "evolution_actions"
        ],
        "llm_compare": llm_compare,
        "deterministic_audit": deterministic,
        "compare_summary": compare_summary,
        "external_skill_candidates": external_skill_candidates,
        "evolution_actions": evolution_actions
    }
