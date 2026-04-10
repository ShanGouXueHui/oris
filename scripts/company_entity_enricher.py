#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "insight_entity_registry.json"
FOCUS_PATH = ROOT / "config" / "company_focus_profiles.json"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()

def registry_entities():
    obj = load_json(REGISTRY_PATH)
    if isinstance(obj, dict) and isinstance(obj.get("entities"), list):
        return obj["entities"]
    if isinstance(obj, list):
        return obj
    return []

def focus_profiles():
    return load_json(FOCUS_PATH)

def match_registry(binding: dict):
    name = binding.get("name") or binding.get("display_name") or ""
    aliases = binding.get("aliases") or []
    probe = {norm(name), *[norm(x) for x in aliases if x]}
    for item in registry_entities():
        vals = {norm(item.get("name"))}
        vals.update(norm(x) for x in (item.get("aliases") or []) if x)
        if probe & vals:
            return item
    return None

def infer_focus_profile(prompt_text: str, registry_item: dict | None):
    fp = focus_profiles()
    profiles = fp.get("profiles") or {}
    if registry_item and registry_item.get("focus_profile") in profiles:
        return registry_item.get("focus_profile")

    text = norm(prompt_text)
    for key, cfg in profiles.items():
        for kw in (cfg.get("keyword_hints") or []):
            if norm(kw) and norm(kw) in text:
                return key
    return fp.get("default_profile") or "generic_company"

def enrich_binding(binding: dict, prompt_text: str):
    registry_item = match_registry(binding)
    focus_profile = infer_focus_profile(prompt_text, registry_item)

    out = dict(binding)
    out["focus_profile"] = focus_profile

    if registry_item:
        out["name"] = registry_item.get("name") or out.get("name")
        out["display_name"] = registry_item.get("name") or out.get("display_name") or out.get("name")
        out["aliases"] = registry_item.get("aliases") or out.get("aliases") or []
        out["domain"] = registry_item.get("domain")
        out["region"] = registry_item.get("region")
        out["sources"] = registry_item.get("sources") or []
        out["role_tags"] = registry_item.get("role_tags") or []
        out["default_related_entities"] = registry_item.get("default_related_entities") or {}
        out["registry_match"] = True
    else:
        out.setdefault("sources", [])
        out.setdefault("role_tags", ["company"])
        out.setdefault("default_related_entities", {})
        out["registry_match"] = False

    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", required=True)
    args = ap.parse_args()

    payload = json.loads(args.input_json)
    binding = payload.get("binding") or {}
    prompt_text = payload.get("prompt_text") or ""

    enriched = enrich_binding(binding, prompt_text)
    print(json.dumps({
        "ok": True,
        "binding": enriched
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
