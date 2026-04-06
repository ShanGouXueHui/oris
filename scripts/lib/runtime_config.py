#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "bridge_runtime.json"
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"

def load_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def config():
    return load_json(CONFIG_PATH, {})

def root_path() -> Path:
    return ROOT

def rel_path(key: str) -> Path:
    cfg = config()
    rel = ((cfg.get("paths") or {}).get(key))
    if not rel:
        raise KeyError(f"missing config.paths.{key}")
    return ROOT / rel

def local_service_url(key: str) -> str:
    cfg = config()
    value = ((cfg.get("local_services") or {}).get(key))
    if not value:
        raise KeyError(f"missing config.local_services.{key}")
    return value

def local_service_value(key: str):
    cfg = config()
    if key not in (cfg.get("local_services") or {}):
        raise KeyError(f"missing config.local_services.{key}")
    return (cfg.get("local_services") or {}).get(key)

def default_source(key: str) -> str:
    cfg = config()
    value = (((cfg.get("bridges") or {}).get("default_sources") or {}).get(key))
    if not value:
        raise KeyError(f"missing config.bridges.default_sources.{key}")
    return value

def bridge_execution_flag(key: str, default=False):
    cfg = config()
    return bool((((cfg.get("bridges") or {}).get("execution") or {}).get(key, default)))

def role_routing():
    return (((config().get("bridges") or {}).get("role_routing")) or {})

def exact_reply_patterns():
    return ((((config().get("bridges") or {}).get("reply_rules") or {}).get("exact_reply_patterns")) or [])

def feishu_api(key: str):
    cfg = config()
    value = ((cfg.get("feishu") or {}).get(key))
    if value is None:
        raise KeyError(f"missing config.feishu.{key}")
    return value

def secrets():
    return load_json(SECRETS_PATH, {})

def openclaw_config():
    return load_json(OPENCLAW_CONFIG_PATH, {})

def deep_get(data, path):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

def read_oris_api_key():
    data = secrets()
    return (((data.get("services") or {}).get("oris_api") or {}).get("bearerToken"))

def read_feishu_creds():
    cfg = openclaw_config()
    sec = secrets()

    app_id_candidates = [
        ["channels", "feishu", "accounts", "main", "appId"],
        ["channels", "feishu", "appId"]
    ]
    app_secret_candidates = [
        ["channels", "feishu", "accounts", "main", "appSecret"],
        ["channels", "feishu", "appSecret"],
        ["channels", "feishu", "accounts", "main", "app_secret"],
        ["channels", "feishu", "app_secret"]
    ]

    app_id = None
    for p in app_id_candidates:
        v = deep_get(cfg, p)
        if isinstance(v, str) and v.strip():
            app_id = v.strip()
            break
    if not app_id:
        for p in app_id_candidates:
            v = deep_get(sec, p)
            if isinstance(v, str) and v.strip():
                app_id = v.strip()
                break

    app_secret = None
    for p in app_secret_candidates:
        v = deep_get(sec, p)
        if isinstance(v, str) and v.strip():
            app_secret = v.strip()
            break

    return app_id, app_secret

def read_feishu_verification_token():
    cfg = openclaw_config()
    sec = secrets()

    candidates = [
        ["channels", "feishu", "verificationToken"],
        ["channels", "feishu", "accounts", "main", "verificationToken"],
    ]

    for p in candidates:
        v = deep_get(sec, p)
        if isinstance(v, str) and v.strip():
            return v.strip()

    for p in candidates:
        v = deep_get(cfg, p)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return None
