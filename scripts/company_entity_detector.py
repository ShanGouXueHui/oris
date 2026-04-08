#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPANY_CFG_PATH = ROOT / "config" / "company_entity_detection.json"
RESOLUTION_CFG_PATH = ROOT / "config" / "entity_resolution.json"


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_json_text(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start:end+1])
        except Exception:
            return None
    return None


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u3000", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def lower_key(s: str) -> str:
    return norm_text(s).lower()


def contains_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s or "")


def read_cfg():
    company_cfg = load_json(COMPANY_CFG_PATH, {})
    resolution = load_json(RESOLUTION_CFG_PATH, {})
    detector_cfg = (resolution.get("company_detector") or {}) if isinstance(resolution, dict) else {}
    return company_cfg, detector_cfg


def get_hf_token(company_cfg: dict) -> str:
    for key in company_cfg.get("hf_token_env_keys", []):
        v = os.environ.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    secrets_path = Path.home() / ".openclaw" / "secrets.json"
    if secrets_path.exists():
        try:
            obj = json.loads(secrets_path.read_text(encoding="utf-8"))
            for key in company_cfg.get("hf_token_secret_keys", []):
                v = obj.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        except Exception:
            pass
    return ""


def cleanup_candidate(name: str, company_cfg: dict, detector_cfg: dict) -> str:
    s = norm_text(name)
    s = s.strip("：:，,。.;；!！?？()（）[]【】<>《》\"'` ")
    changed = True
    while changed and s:
        changed = False
        for prefix in company_cfg.get("cleanup_prefixes", []):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()
                changed = True
        for suffix in (company_cfg.get("cleanup_suffixes", []) + detector_cfg.get("cleanup_suffixes", [])):
            if s.endswith(suffix):
                s = s[:-len(suffix)].strip()
                changed = True
    s = s.strip("：:，,。.;；!！?？()（）[]【】<>《》\"'` ")
    return s


def is_negative_term(name: str, company_cfg: dict, detector_cfg: dict) -> bool:
    s = lower_key(name)
    if not s:
        return True

    block_terms = []
    for item in company_cfg.get("negative_terms", []):
        if isinstance(item, str) and item.strip():
            block_terms.append(lower_key(item))
    for item in detector_cfg.get("blocklist", []):
        if isinstance(item, str) and item.strip():
            block_terms.append(lower_key(item))

    if s in block_terms:
        return True

    if len(s) < int(company_cfg.get("min_alias_length", 2)):
        return True

    return False


def iter_registry_entities(obj):
    if isinstance(obj, dict):
        name = obj.get("name") or obj.get("canonical_name") or obj.get("display_name") or obj.get("entity")
        aliases = obj.get("aliases") or []
        if isinstance(name, str) and name.strip():
            role = obj.get("role") or obj.get("type") or obj.get("entity_type")
            if role in (None, "company", "organization", "vendor", "target_company", "competitor", "partner", "cloud_vendor"):
                yield {
                    "canonical": norm_text(name),
                    "aliases": [norm_text(x) for x in aliases if isinstance(x, str) and x.strip()]
                }
        for v in obj.values():
            yield from iter_registry_entities(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_registry_entities(item)


def build_alias_index(company_cfg: dict):
    alias_to_canonical = {}
    canonical_to_aliases = {}

    registry_path = company_cfg.get("entity_registry_path")
    if isinstance(registry_path, str) and registry_path.strip():
        rp = Path(registry_path)
        if not rp.is_absolute():
            rp = ROOT / rp
        registry_obj = load_json(rp, {})
        for item in iter_registry_entities(registry_obj):
            canonical = item["canonical"]
            aliases = [canonical] + item["aliases"]
            canonical_to_aliases.setdefault(canonical, [])
            for a in aliases:
                if a and a not in canonical_to_aliases[canonical]:
                    canonical_to_aliases[canonical].append(a)

    strong_aliases = company_cfg.get("strong_aliases") or {}
    if isinstance(strong_aliases, dict):
        for canonical, aliases in strong_aliases.items():
            c = norm_text(canonical)
            canonical_to_aliases.setdefault(c, [])
            for a in [c] + [x for x in (aliases or []) if isinstance(x, str)]:
                a2 = norm_text(a)
                if a2 and a2 not in canonical_to_aliases[c]:
                    canonical_to_aliases[c].append(a2)

    for canonical, aliases in canonical_to_aliases.items():
        for a in aliases:
            alias_to_canonical[lower_key(a)] = canonical

    return alias_to_canonical, canonical_to_aliases


def alias_in_text(alias: str, text: str) -> bool:
    alias = norm_text(alias)
    text = norm_text(text)
    if not alias or not text:
        return False
    if contains_cjk(alias):
        return alias in text
    pattern = r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def contains_compare_prompt(text: str, company_cfg: dict) -> bool:
    s = norm_text(text)
    lower = s.lower()
    for marker in company_cfg.get("compare_markers", []):
        if marker in s or marker.lower() in lower:
            return True
    return False


def alias_detect(text: str, company_cfg: dict, detector_cfg: dict, alias_to_canonical: dict, canonical_to_aliases: dict):
    hits = []
    seen = set()
    for alias_key, canonical in alias_to_canonical.items():
        alias = alias_key
        real_alias = None
        for a in canonical_to_aliases.get(canonical, []):
            if lower_key(a) == alias_key:
                real_alias = a
                break
        real_alias = real_alias or alias_key
        if alias_in_text(real_alias, text):
            key = (canonical, real_alias)
            if key not in seen:
                seen.add(key)
                hits.append({"canonical": canonical, "alias": real_alias})

    canonicals = []
    for item in hits:
        if not is_negative_term(item["canonical"], company_cfg, detector_cfg):
            canonicals.append(item["canonical"])
    canonicals = list(dict.fromkeys(canonicals))

    if not canonicals:
        return None

    if len(canonicals) > 1:
        return {
            "ok": False,
            "blocked": True,
            "reason": "ambiguous_alias_candidates",
            "method": "registry_alias",
            "confidence": 0.0,
            "target_company": "unknown",
            "canonical_name": "",
            "aliases": canonicals,
            "candidates": hits,
        }

    canonical = canonicals[0]
    return {
        "ok": True,
        "blocked": False,
        "reason": "alias_match",
        "method": "registry_alias",
        "confidence": 0.99,
        "target_company": canonical,
        "canonical_name": canonical,
        "aliases": canonical_to_aliases.get(canonical, [canonical]),
        "candidates": hits,
    }


def ensure_gliner_model(company_cfg: dict, detector_cfg: dict) -> str:
    gliner_cfg = detector_cfg.get("gliner") or {}
    local_dir = gliner_cfg.get("local_dir")
    model_name = gliner_cfg.get("model_name") or "urchade/gliner_medium-v2.1"

    if isinstance(local_dir, str) and local_dir.strip():
        p = Path(os.path.expanduser(local_dir)).resolve()
        if p.exists():
            return str(p)

    if not gliner_cfg.get("auto_download_if_missing", True):
        return model_name

    from huggingface_hub import snapshot_download
    token = get_hf_token(company_cfg)
    dl = snapshot_download(repo_id=model_name, token=token or None)
    return dl


@lru_cache(maxsize=1)
def load_gliner_model(model_ref: str):
    try:
        from gliner import GLiNER
    except Exception:
        from GLiNER import GLiNER
    return GLiNER.from_pretrained(model_ref)


def canonicalize_candidate(name: str, alias_to_canonical: dict) -> str:
    key = lower_key(name)
    return alias_to_canonical.get(key) or norm_text(name)


def gliner_detect(text: str, company_cfg: dict, detector_cfg: dict, alias_to_canonical: dict, canonical_to_aliases: dict):
    gliner_cfg = detector_cfg.get("gliner") or {}
    if not gliner_cfg.get("enabled", False):
        return None

    prepared = norm_text(text)[: int(gliner_cfg.get("max_text_length", 1200))]
    if not prepared:
        return None

    model_ref = ensure_gliner_model(company_cfg, detector_cfg)
    model = load_gliner_model(model_ref)
    labels = gliner_cfg.get("candidate_labels") or ["company", "organization"]
    threshold = float(gliner_cfg.get("threshold", 0.45))

    raw = model.predict_entities(prepared, labels, threshold=threshold) or []

    candidates = []
    for item in raw:
        raw_text = item.get("text") or ""
        cleaned = cleanup_candidate(raw_text, company_cfg, detector_cfg)
        if not cleaned or is_negative_term(cleaned, company_cfg, detector_cfg):
            continue

        canonical = canonicalize_candidate(cleaned, alias_to_canonical)
        if is_negative_term(canonical, company_cfg, detector_cfg):
            continue

        score = float(item.get("score") or 0.0)
        label = item.get("label") or ""
        candidates.append({
            "raw_text": raw_text,
            "cleaned": cleaned,
            "canonical": canonical,
            "label": label,
            "score": score
        })

    if not candidates:
        return None

    merged = {}
    for c in candidates:
        key = c["canonical"]
        cur = merged.get(key)
        if not cur or c["score"] > cur["score"]:
            merged[key] = c

    ranked = sorted(merged.values(), key=lambda x: (-x["score"], -len(x["canonical"])))
    top = ranked[0]
    gap = float(company_cfg.get("ambiguous_gap", 0.08))

    if len(ranked) > 1:
        second = ranked[1]
        if contains_compare_prompt(text, company_cfg) or abs(top["score"] - second["score"]) <= gap:
            return {
                "ok": False,
                "blocked": True,
                "reason": "ambiguous_gliner_candidates",
                "method": "gliner",
                "confidence": top["score"],
                "target_company": "unknown",
                "canonical_name": "",
                "aliases": [],
                "candidates": ranked[:8],
            }

    return {
        "ok": True,
        "blocked": False,
        "reason": "gliner_match",
        "method": "gliner",
        "confidence": top["score"],
        "target_company": top["canonical"],
        "canonical_name": top["canonical"],
        "aliases": canonical_to_aliases.get(top["canonical"], [top["canonical"]]),
        "candidates": ranked[:8],
    }


def regex_detect(text: str, company_cfg: dict, detector_cfg: dict, alias_to_canonical: dict, canonical_to_aliases: dict):
    rx_cfg = detector_cfg.get("regex_fallback") or {}
    if not rx_cfg.get("enabled", False):
        return None

    for pattern in rx_cfg.get("patterns", []):
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            continue
        candidate = cleanup_candidate(m.group(1), company_cfg, detector_cfg)
        if not candidate or is_negative_term(candidate, company_cfg, detector_cfg):
            continue
        canonical = canonicalize_candidate(candidate, alias_to_canonical)
        if is_negative_term(canonical, company_cfg, detector_cfg):
            continue
        return {
            "ok": True,
            "blocked": False,
            "reason": "regex_match",
            "method": "regex_fallback",
            "confidence": 0.70,
            "target_company": canonical,
            "canonical_name": canonical,
            "aliases": canonical_to_aliases.get(canonical, [canonical]),
            "candidates": [{"pattern": pattern, "candidate": candidate, "canonical": canonical}],
        }
    return None


def llm_arbitration(
    text: str,
    company_cfg: dict,
    detector_cfg: dict,
    alias_to_canonical: dict,
    canonical_to_aliases: dict
):
    llm_cfg = detector_cfg.get("llm_arbitration") or {}
    if not llm_cfg.get("enabled", False):
        return None

    if contains_compare_prompt(text, company_cfg) and not llm_cfg.get("allow_on_compare_requests", False):
        return {
            "ok": False,
            "blocked": True,
            "reason": company_cfg.get("compare_block_reason_code", "compare_request_not_single_company"),
            "method": "llm_arbitration",
            "confidence": 0.0,
            "target_company": "unknown",
            "canonical_name": "",
            "aliases": [],
            "candidates": [],
        }

    infer_script = llm_cfg.get("infer_script") or "scripts/oris_infer.py"
    infer_path = Path(infer_script)
    if not infer_path.is_absolute():
        infer_path = ROOT / infer_path

    prompt_template = company_cfg.get("llm_arbitration_prompt_template") or company_cfg.get("prompt_template") or ""
    arbitration_prompt = prompt_template.replace("{{text}}", text)

    cmd = [
        "python3",
        str(infer_path),
        "--role",
        llm_cfg.get("role", "free_fallback"),
        "--prompt",
        arbitration_prompt,
        "--source",
        "company_entity_llm_arbitration"
    ]

    timeout_seconds = int(llm_cfg.get("timeout_seconds", 90))
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(ROOT),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        if llm_cfg.get("fail_closed", True):
            return {
                "ok": False,
                "blocked": True,
                "reason": "llm_arbitration_timeout",
                "method": "llm_arbitration",
                "confidence": 0.0,
                "target_company": "unknown",
                "canonical_name": "",
                "aliases": [],
                "candidates": [],
            }
        return None

    outer = parse_json_text(r.stdout)
    if r.returncode != 0 or not isinstance(outer, dict) or not outer.get("ok"):
        if llm_cfg.get("fail_closed", True):
            return {
                "ok": False,
                "blocked": True,
                "reason": "llm_arbitration_inference_failed",
                "method": "llm_arbitration",
                "confidence": 0.0,
                "target_company": "unknown",
                "canonical_name": "",
                "aliases": [],
                "candidates": [],
            }
        return None

    raw_text = ((outer.get("text") or "") if isinstance(outer.get("text"), str) else "")
    inner = parse_json_text(raw_text) if llm_cfg.get("parse_json_from_text", True) else None
    if not isinstance(inner, dict):
        if llm_cfg.get("fail_closed", True):
            return {
                "ok": False,
                "blocked": True,
                "reason": "llm_arbitration_output_not_json",
                "method": "llm_arbitration",
                "confidence": 0.0,
                "target_company": "unknown",
                "canonical_name": "",
                "aliases": [],
                "candidates": [],
            }
        return None

    candidate = cleanup_candidate(inner.get("target_company") or "", company_cfg, detector_cfg)
    if not candidate or lower_key(candidate) == "unknown" or is_negative_term(candidate, company_cfg, detector_cfg):
        return {
            "ok": False,
            "blocked": True,
            "reason": "llm_arbitration_unknown",
            "method": "llm_arbitration",
            "confidence": float(inner.get("confidence") or 0.0),
            "target_company": "unknown",
            "canonical_name": "",
            "aliases": [],
            "candidates": [],
        }

    canonical = canonicalize_candidate(candidate, alias_to_canonical)
    if is_negative_term(canonical, company_cfg, detector_cfg):
        return {
            "ok": False,
            "blocked": True,
            "reason": "llm_arbitration_negative_term",
            "method": "llm_arbitration",
            "confidence": float(inner.get("confidence") or 0.0),
            "target_company": "unknown",
            "canonical_name": "",
            "aliases": [],
            "candidates": [],
        }

    aliases = inner.get("aliases") if isinstance(inner.get("aliases"), list) else []
    aliases = [x for x in aliases if isinstance(x, str) and x.strip()]
    if not aliases:
        aliases = canonical_to_aliases.get(canonical, [canonical])

    return {
        "ok": True,
        "blocked": False,
        "reason": inner.get("reason") or "llm_arbitration_match",
        "method": "llm_arbitration",
        "confidence": float(inner.get("confidence") or 0.0),
        "target_company": canonical,
        "canonical_name": canonical,
        "aliases": aliases,
        "candidates": [{
            "raw_text": raw_text[:500],
            "canonical": canonical
        }],
    }


def detect_target_company(text: str):
    company_cfg, detector_cfg = read_cfg()
    alias_to_canonical, canonical_to_aliases = build_alias_index(company_cfg)
    provider_order = detector_cfg.get("provider_order") or ["registry_alias", "gliner", "regex_fallback", "llm_arbitration"]
    normalized_text = norm_text(text)

    if not normalized_text:
        return {
            "ok": False,
            "blocked": True,
            "reason": "empty_input",
            "method": "none",
            "confidence": 0.0,
            "target_company": "unknown",
            "canonical_name": "",
            "aliases": [],
            "candidates": [],
        }

    if company_cfg.get("block_compare_requests", True) and contains_compare_prompt(normalized_text, company_cfg):
        return {
            "ok": False,
            "blocked": True,
            "reason": company_cfg.get("compare_block_reason_code", "compare_request_not_single_company"),
            "method": "precheck_compare_block",
            "confidence": 0.0,
            "target_company": "unknown",
            "canonical_name": "",
            "aliases": [],
            "candidates": [],
            "provider_order": provider_order,
            "input_text": normalized_text[:500],
        }

    for provider in provider_order:
        if provider == "registry_alias":
            result = alias_detect(normalized_text, company_cfg, detector_cfg, alias_to_canonical, canonical_to_aliases)
        elif provider == "gliner":
            result = gliner_detect(normalized_text, company_cfg, detector_cfg, alias_to_canonical, canonical_to_aliases)
        elif provider == "regex_fallback":
            result = regex_detect(normalized_text, company_cfg, detector_cfg, alias_to_canonical, canonical_to_aliases)
        elif provider == "llm_arbitration":
            result = llm_arbitration(normalized_text, company_cfg, detector_cfg, alias_to_canonical, canonical_to_aliases)
        else:
            result = None

        if not result:
            continue

        result["provider_order"] = provider_order
        result["input_text"] = normalized_text[:500]

        if result.get("ok"):
            min_conf = float(company_cfg.get("min_confidence", 0.60))
            if float(result.get("confidence") or 0.0) < min_conf and result.get("method") != "registry_alias":
                return {
                    "ok": False,
                    "blocked": True,
                    "reason": "low_confidence",
                    "method": result.get("method"),
                    "confidence": result.get("confidence") or 0.0,
                    "target_company": "unknown",
                    "canonical_name": "",
                    "aliases": [],
                    "candidates": result.get("candidates") or [],
                    "provider_order": provider_order,
                    "input_text": normalized_text[:500],
                }
            return result

        if result.get("blocked"):
            return result

    return {
        "ok": False,
        "blocked": True,
        "reason": "unknown_target_company",
        "method": "none",
        "confidence": 0.0,
        "target_company": "unknown",
        "canonical_name": "",
        "aliases": [],
        "candidates": [],
        "provider_order": provider_order,
        "input_text": normalized_text[:500],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    args = ap.parse_args()
    print(json.dumps(detect_target_company(args.text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
