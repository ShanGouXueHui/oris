#!/usr/bin/env python3
import argparse
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.oris_llm_client import call_oris_text

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "config" / "insight_methodology_rules.json"
PROFILES_PATH = ROOT / "config" / "insight_case_profiles.json"
ENTITY_REGISTRY_PATH = ROOT / "config" / "insight_entity_registry.json"
COMPILER_RUNTIME_PATH = ROOT / "config" / "insight_compiler_runtime.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def ts_compact():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def normalize_text(text: str):
    return re.sub(r"\s+", " ", text or "").strip()

def ascii_slug(value: str, max_len: int = 48):
    value = re.sub(r"[^A-Za-z0-9]+", "-", value or "").strip("-").lower()
    if not value:
        value = "case"
    return value[:max_len].strip("-") or "case"

def text_digest(text: str, n: int = 10):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:n]

def detect_deliverables(text: str, default_items: list):
    lower = text.lower()
    out = []
    if any(k in lower or k in text for k in ["word", "docx", "报告", "洞察报告"]):
        out.append("word")
    if any(k in lower or k in text for k in ["excel", "xlsx", "底表", "证据表", "数据表"]):
        out.append("excel")
    if any(k in lower or k in text for k in ["ppt", "汇报", "交流ppt", "简报", "deck"]):
        out.append("ppt")
    if not out:
        out = list(default_items or ["word", "excel", "ppt"])
    return sorted(dict.fromkeys(out), key=out.index)

def extract_numbered_items(text: str):
    matches = re.findall(r'(\d+[）\.\、])\s*(.*?)(?=(?:\s*\d+[）\.\、]\s*)|$)', text, flags=re.S)
    out = []
    for _, item in matches:
        item = normalize_text(item)
        if item:
            out.append(item)
    return out

def choose_profile(text: str, profiles: dict):
    lower = text.lower()
    scores = []
    for code, profile in (profiles.get("profiles") or {}).items():
        keywords = profile.get("intent_keywords_any") or []
        score = sum(1 for k in keywords if k.lower() in lower or k in text)
        scores.append({"profile_code": code, "score": score})
    scores.sort(key=lambda x: x["score"], reverse=True)
    if scores and scores[0]["score"] > 0:
        return scores[0]["profile_code"], scores
    return profiles.get("default_profile", "company_profile"), scores

def registry_index(registry: dict):
    by_name = {}
    by_alias_lower = {}
    for entity in registry.get("entities") or []:
        name = entity.get("name")
        if name:
            by_name[name] = entity
        for alias in entity.get("aliases") or [name]:
            if alias:
                by_alias_lower[alias.lower()] = entity
    return by_name, by_alias_lower

def detect_entities(text: str, registry: dict):
    found = []
    used = set()
    lower = text.lower()
    by_name, by_alias_lower = registry_index(registry)

    for alias_lower, entity in by_alias_lower.items():
        if alias_lower in lower:
            if entity["name"] not in used:
                found.append(entity)
                used.add(entity["name"])

    english_candidates = re.findall(r'\b[A-Z][A-Za-z0-9&\.-]*(?:\s+[A-Z][A-Za-z0-9&\.-]*){0,4}\b', text)
    for cand in english_candidates:
        cand = normalize_text(cand)
        if len(cand) < 3:
            continue
        if cand in used:
            continue
        if cand.lower() in {"word", "excel", "ppt"}:
            continue
        found.append({
            "name": cand,
            "aliases": [cand],
            "role_tags": ["company"],
            "domain": None,
            "region": None,
            "sources": []
        })
        used.add(cand)

    return found

def assign_roles(profile_code: str, detected_entities: list, profiles: dict):
    out = {
        "partner": None,
        "cloud_vendor": None,
        "customers": [],
        "competitors": [],
        "target_company": None
    }

    profile = (profiles.get("profiles") or {}).get(profile_code) or {}
    role_priority = profile.get("role_priority") or {}

    def match_first(target_tags):
        for entity in detected_entities:
            tags = set(entity.get("role_tags") or [])
            if any(tag in tags for tag in target_tags):
                return entity
        return None

    if profile_code == "account_strategy_partner_cloud_customer":
        out["partner"] = match_first(role_priority.get("partner") or [])
        out["cloud_vendor"] = match_first(role_priority.get("cloud_vendor") or [])
        for entity in detected_entities:
            tags = set(entity.get("role_tags") or [])
            if any(tag in tags for tag in (role_priority.get("customer") or [])):
                out["customers"].append(entity)
            elif any(tag in tags for tag in (role_priority.get("competitor") or [])):
                out["competitors"].append(entity)
        return out

    if profile_code == "company_profile":
        out["target_company"] = detected_entities[0] if detected_entities else None
        return out

    if profile_code == "competitor_benchmark":
        out["target_company"] = detected_entities[0] if detected_entities else None
        if len(detected_entities) > 1:
            out["competitors"] = detected_entities[1:]
        return out

    if detected_entities:
        out["target_company"] = detected_entities[0]
    return out

def dedup_entities(items: list):
    out = []
    used = set()
    for item in items:
        name = item.get("name")
        if not name or name in used:
            continue
        out.append(item)
        used.add(name)
    return out

def expand_default_related_entities(role_bindings: dict, registry: dict):
    by_name, _ = registry_index(registry)
    partner = role_bindings.get("partner")
    if not partner:
        return role_bindings
    defaults = partner.get("default_related_entities") or {}

    if not role_bindings.get("competitors"):
        role_bindings["competitors"] = [
            by_name[name] for name in (defaults.get("competitors") or [])
            if name in by_name
        ]
    if not role_bindings.get("cloud_vendor"):
        clouds = [by_name[name] for name in (defaults.get("cloud_vendors") or []) if name in by_name]
        if clouds:
            role_bindings["cloud_vendor"] = clouds[0]
    if not role_bindings.get("customers"):
        role_bindings["customers"] = [
            by_name[name] for name in (defaults.get("customer_examples") or [])
            if name in by_name
        ]

    role_bindings["competitors"] = dedup_entities(role_bindings.get("competitors") or [])
    role_bindings["customers"] = dedup_entities(role_bindings.get("customers") or [])
    return role_bindings

def build_case_code(profile, role_bindings, prompt_text):
    analysis_type = profile.get("analysis_type", "insight")
    digest = text_digest(prompt_text, 10)

    parts = [analysis_type]
    partner = (role_bindings.get("partner") or {}).get("name")
    cloud = (role_bindings.get("cloud_vendor") or {}).get("name")
    target = (role_bindings.get("target_company") or {}).get("name")
    customers = role_bindings.get("customers") or []

    if partner:
        parts.append(ascii_slug(partner, 20))
    if cloud:
        parts.append(ascii_slug(cloud, 20))
    if target and not partner:
        parts.append(ascii_slug(target, 24))
    if customers:
        parts.append(ascii_slug(customers[0].get("name", "customer"), 20))
    parts.append(digest)
    return "-".join([p for p in parts if p])[:96].strip("-")

def safe_json_from_text(text: str):
    if not text:
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

def llm_compare_parse(prompt_text: str, registry: dict, compiler_runtime: dict):
    if not compiler_runtime.get("llm_compare_enabled"):
        return {"ok": False, "skipped": True, "reason": "llm_compare_disabled"}

    entity_names = [x.get("name") for x in (registry.get("entities") or []) if x.get("name")]
    role = compiler_runtime.get("llm_compare_role", "free_fallback")
    timeout_seconds = int(compiler_runtime.get("llm_compare_timeout_seconds", 180))

    llm_prompt = f"""
你是商业洞察编译器。请把下面自然语言需求解析成JSON，不要输出解释文字。
只允许输出如下JSON结构：
{{
  "profile_code": "account_strategy_partner_cloud_customer|company_profile|competitor_benchmark|company_profile",
  "deliverables": ["word","excel","ppt"],
  "questions": ["..."],
  "primary_company": "公司名或空",
  "partner": "公司名或空",
  "cloud_vendor": "公司名或空",
  "customers": ["公司名"],
  "competitors": ["公司名"]
}}

候选实体名单：
{json.dumps(entity_names, ensure_ascii=False)}

用户prompt：
{prompt_text}
""".strip()

    try:
        resp = call_oris_text(llm_prompt, role=role, timeout_seconds=timeout_seconds)
        if not resp.get("ok"):
            return {"ok": False, "error": resp.get("error")}
        parsed = safe_json_from_text(resp.get("text", ""))
        if not parsed:
            return {"ok": False, "error": "llm_output_not_json", "text": resp.get("text", "")[:1200]}
        return {"ok": True, "parsed": parsed}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def pick_registry_entity(name: str, registry: dict):
    if not name:
        return None
    by_name, by_alias_lower = registry_index(registry)
    if name in by_name:
        return by_name[name]
    return by_alias_lower.get(name.lower())

def hybrid_merge(compiled: dict, llm_result: dict, registry: dict, compiler_runtime: dict):
    merged = False
    merge_notes = []
    if not llm_result.get("ok"):
        return compiled, {"merged": False, "merge_notes": merge_notes}

    llm = llm_result.get("parsed") or {}
    policy = compiler_runtime.get("merge_policy") or {}
    rb = compiled["role_bindings"]

    if compiled["profile_code"] == "company_profile" and not rb.get("target_company") and policy.get("fill_missing_target_company_from_llm", True):
        ent = pick_registry_entity(llm.get("primary_company"), registry)
        if ent:
            rb["target_company"] = ent
            merged = True
            merge_notes.append(f"filled target_company from llm: {ent['name']}")

    if compiled["profile_code"] == "account_strategy_partner_cloud_customer":
        if not rb.get("partner"):
            ent = pick_registry_entity(llm.get("partner"), registry)
            if ent:
                rb["partner"] = ent
                merged = True
                merge_notes.append(f"filled partner from llm: {ent['name']}")
        if not rb.get("cloud_vendor"):
            ent = pick_registry_entity(llm.get("cloud_vendor"), registry)
            if ent:
                rb["cloud_vendor"] = ent
                merged = True
                merge_notes.append(f"filled cloud_vendor from llm: {ent['name']}")
        if not rb.get("customers") and policy.get("fill_missing_customers_from_llm", True):
            customers = []
            for name in llm.get("customers") or []:
                ent = pick_registry_entity(name, registry)
                if ent:
                    customers.append(ent)
            if customers:
                rb["customers"] = dedup_entities(customers)
                merged = True
                merge_notes.append("filled customers from llm")
        if not rb.get("competitors") and policy.get("fill_missing_competitors_from_llm", True):
            competitors = []
            for name in llm.get("competitors") or []:
                ent = pick_registry_entity(name, registry)
                if ent:
                    competitors.append(ent)
            if competitors:
                rb["competitors"] = dedup_entities(competitors)
                merged = True
                merge_notes.append("filled competitors from llm")

    if not compiled.get("deliverables") and policy.get("fill_missing_deliverables_from_llm", True):
        compiled["deliverables"] = llm.get("deliverables") or compiled.get("deliverables") or []
        if compiled["deliverables"]:
            merged = True
            merge_notes.append("filled deliverables from llm")

    compiled["role_bindings"] = rb
    return compiled, {"merged": merged, "merge_notes": merge_notes}

def build_case(prompt_text: str):
    rules = load_json(RULES_PATH)
    profiles = load_json(PROFILES_PATH)
    registry = load_json(ENTITY_REGISTRY_PATH)
    compiler_runtime = load_json(COMPILER_RUNTIME_PATH)

    trace = []
    ambiguity_flags = []

    trace.append({"stage": "raw_prompt", "value": prompt_text})
    normalized_prompt = normalize_text(prompt_text)
    trace.append({"stage": "normalized_prompt", "value": normalized_prompt})

    profile_code, profile_scores = choose_profile(normalized_prompt, profiles)
    profile = (profiles.get("profiles") or {}).get(profile_code) or {}
    trace.append({"stage": "profile_selection", "selected_profile": profile_code, "profile_scores": profile_scores})

    deliverables = detect_deliverables(normalized_prompt, profile.get("deliverables_default") or [])
    trace.append({"stage": "deliverable_detection", "deliverables": deliverables})

    questions = extract_numbered_items(normalized_prompt)
    trace.append({"stage": "question_extraction", "questions": questions})

    detected_entities = dedup_entities(detect_entities(normalized_prompt, registry))
    trace.append({"stage": "entity_detection", "detected_entities": [x.get("name") for x in detected_entities]})

    role_bindings_initial = assign_roles(profile_code, detected_entities, profiles)
    trace.append({
        "stage": "role_binding_initial",
        "role_bindings_initial": {
            "partner": (role_bindings_initial.get("partner") or {}).get("name"),
            "cloud_vendor": (role_bindings_initial.get("cloud_vendor") or {}).get("name"),
            "customers": [x.get("name") for x in (role_bindings_initial.get("customers") or [])],
            "competitors": [x.get("name") for x in (role_bindings_initial.get("competitors") or [])],
            "target_company": (role_bindings_initial.get("target_company") or {}).get("name")
        }
    })

    role_bindings = expand_default_related_entities(role_bindings_initial, registry)
    trace.append({
        "stage": "role_binding_after_default_expansion",
        "role_bindings_after_default_expansion": {
            "partner": (role_bindings.get("partner") or {}).get("name"),
            "cloud_vendor": (role_bindings.get("cloud_vendor") or {}).get("name"),
            "customers": [x.get("name") for x in (role_bindings.get("customers") or [])],
            "competitors": [x.get("name") for x in (role_bindings.get("competitors") or [])],
            "target_company": (role_bindings.get("target_company") or {}).get("name")
        }
    })

    methodology_profile = rules.get("default_methodology_profile")
    title = normalized_prompt[:160]
    case_code = build_case_code(profile, role_bindings, normalized_prompt)
    compiled_case_dir = f"{ts_compact()}_{text_digest(normalized_prompt, 12)}"

    compiled = {
        "ok": True,
        "schema_version": "v1",
        "ts": utc_now(),
        "parser_mode": compiler_runtime.get("parser_mode"),
        "execution_mode": compiler_runtime.get("current_execution_mode"),
        "llm_compare_enabled": compiler_runtime.get("llm_compare_enabled", False),
        "ambiguity_flags": ambiguity_flags,
        "case_code": case_code,
        "compiled_case_dir": compiled_case_dir,
        "title": title,
        "analysis_type": profile.get("analysis_type"),
        "profile_code": profile_code,
        "prompt_text": normalized_prompt,
        "deliverables": deliverables,
        "questions": questions,
        "methodology_profile": methodology_profile,
        "frameworks": ((rules.get("methodology_profiles") or {}).get(methodology_profile) or {}).get("frameworks") or [],
        "report_sections": ((rules.get("methodology_profiles") or {}).get(methodology_profile) or {}).get("report_sections") or [],
        "ppt_sections": ((rules.get("methodology_profiles") or {}).get(methodology_profile) or {}).get("ppt_sections") or [],
        "dimensions": profile.get("default_dimensions") or [],
        "detected_entities": detected_entities,
        "role_bindings": role_bindings,
        "source_priority": ((rules.get("methodology_profiles") or {}).get(methodology_profile) or {}).get("source_priority") or [],
        "authoring_rules": rules.get("authoring_rules") or {},
        "compiler_trace": trace
    }

    llm_result = llm_compare_parse(normalized_prompt, registry, compiler_runtime)
    compiled["compiler_trace"].append({"stage": "llm_compare", "llm_compare_result": llm_result})

    compiled, merge_info = hybrid_merge(compiled, llm_result, registry, compiler_runtime)
    compiled["compiler_trace"].append({"stage": "hybrid_merge", "hybrid_merge": merge_info})

    compiled["compiler_trace"].append({
        "stage": "case_assembly",
        "case_code": compiled["case_code"],
        "compiled_case_dir": compiled["compiled_case_dir"]
    })

    return compiled

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-text")
    ap.add_argument("--input-file")
    ap.add_argument("--write-output", action="store_true")
    args = ap.parse_args()

    if args.prompt_text:
        prompt_text = args.prompt_text
    elif args.input_file:
        prompt_text = Path(args.input_file).read_text(encoding="utf-8")
    else:
        raise SystemExit("must provide --prompt-text or --input-file")

    out = build_case(prompt_text)

    if args.write_output:
        out_dir = ROOT / "outputs" / "compiled_prompt_cases" / out["compiled_case_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "compiled_case.json"
        out["compiled_case_path"] = str(out_path.relative_to(ROOT))
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
