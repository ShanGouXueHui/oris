#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "config" / "report_runtime.json"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def cfg_get(data, keys, default=None):
    cur = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def expand_path(root: Path, value: str) -> Path:
    p = Path(os.path.expanduser(value))
    if p.is_absolute():
        return p
    return root / value

def normalize_key_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())

def recursive_find_secret(obj, normalized_targets):
    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = normalize_key_name(k)
            if nk in normalized_targets and isinstance(v, str) and v.strip():
                return v.strip(), k
        for _, v in obj.items():
            found = recursive_find_secret(v, normalized_targets)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = recursive_find_secret(item, normalized_targets)
            if found:
                return found
    return None

def resolve_api_key(cfg):
    auth_cfg = cfg_get(cfg, ["oris_api", "auth"], {}) or {}
    env_var = auth_cfg.get("env_var")
    secrets_json_path = expand_path(ROOT, auth_cfg.get("secrets_json_path", "~/.openclaw/secrets.json"))
    discovery_keys = auth_cfg.get("discovery_keys", [])

    if env_var and os.environ.get(env_var):
        return {"ok": True, "api_key": os.environ.get(env_var)}

    if secrets_json_path.exists():
        data = load_json(secrets_json_path)
        normalized_targets = {normalize_key_name(x) for x in discovery_keys}
        found = recursive_find_secret(data, normalized_targets)
        if found:
            value, _ = found
            return {"ok": True, "api_key": value}

    return {"ok": False, "error": "api_key_not_found"}

def call_oris_text(prompt: str, role: str = "free_fallback", timeout_seconds: int = 180):
    cfg = load_json(CFG_PATH)
    resolved = resolve_api_key(cfg)
    if not resolved.get("ok"):
        return {"ok": False, "error": resolved.get("error", "resolve_api_key_failed")}

    infer_url = cfg_get(cfg, ["oris_api", "infer_url"])
    header_name = cfg_get(cfg, ["oris_api", "auth", "header_name"], "X-ORIS-API-Key")
    source = cfg_get(cfg, ["report", "default_source"], "generic_insight_compiler")

    headers = {
        "Content-Type": "application/json",
        header_name: resolved["api_key"]
    }
    payload = {
        "role": role,
        "prompt": prompt,
        "source": source
    }

    resp = requests.post(infer_url, headers=headers, json=payload, timeout=timeout_seconds)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        return {"ok": False, "error": json.dumps(data, ensure_ascii=False)}
    body = (data.get("data") or {}).get("text", "")
    return {"ok": True, "text": body, "raw": data}
