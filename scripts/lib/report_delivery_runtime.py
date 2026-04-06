#!/usr/bin/env python3
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

import psycopg2

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
OPENCLAW_SECRETS = Path.home() / ".openclaw" / "secrets.json"

def load_json(path, default=None):
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def utc_now():
    return datetime.now(timezone.utc)

def short_hash(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]

def slugify(text):
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in ("-", "_", "."):
            keep.append(ch)
        else:
            keep.append("-")
    s = "".join(keep)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-") or "artifact"

def parse_dsn(s):
    if not isinstance(s, str) or "://" not in s:
        return None
    u = urlparse(s)
    if not u.scheme.startswith("postgres"):
        return None
    return {
        "host": u.hostname or "127.0.0.1",
        "port": int(u.port or 5432),
        "dbname": (u.path or "/").lstrip("/") or "oris_insight",
        "user": unquote(u.username or "oris_app"),
        "password": unquote(u.password or ""),
    }

def dict_to_db(d):
    if not isinstance(d, dict):
        return None
    host = d.get("host") or d.get("hostname")
    port = d.get("port", 5432)
    dbname = d.get("dbname") or d.get("database") or d.get("name")
    user = d.get("user") or d.get("username")
    password = d.get("password", "")
    if host and dbname and user:
        return {
            "host": host,
            "port": int(port),
            "dbname": dbname,
            "user": user,
            "password": password,
        }
    for k in ("dsn", "url", "database_url", "uri", "connection_string"):
        parsed = parse_dsn(d.get(k))
        if parsed:
            return parsed
    return None

def load_insight_storage():
    return load_json(CONFIG_DIR / "insight_storage.json", {})

def extract_db_cfg(raw):
    candidates = [
        raw.get("db"),
        raw.get("postgres"),
        raw.get("database"),
        (raw.get("storage") or {}).get("db"),
        (raw.get("storage") or {}).get("postgres"),
        (raw.get("storage") or {}).get("database"),
        (raw.get("insight") or {}).get("db"),
        (raw.get("insight") or {}).get("postgres"),
    ]
    for item in candidates:
        cfg = dict_to_db(item)
        if cfg:
            return cfg

    for k in ("dsn", "url", "database_url", "uri", "connection_string"):
        cfg = parse_dsn(raw.get(k))
        if cfg:
            return cfg

    raise RuntimeError("config/insight_storage.json missing usable db config")

def db_connect():
    cfg = extract_db_cfg(load_insight_storage())
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg.get("password", ""),
    )

def load_report_runtime():
    raw = load_json(CONFIG_DIR / "report_runtime.json", {})
    nested = raw.get("report_delivery") if isinstance(raw.get("report_delivery"), dict) else {}
    cfg = {
        "public_download_base_url": "https://control.orisfy.com/oris-download",
        "download_path_prefix": "/download",
        "default_link_ttl_hours": 24,
        "sensitive_link_ttl_hours": 2,
        "package_link_ttl_hours": 24,
        "default_max_downloads": 3,
        "package_max_downloads": 2,
        "json_manifest_downloadable": False,
        "allowed_public_extensions": [".docx", ".xlsx", ".zip", ".pdf"],
        "downloadable_channels": ["feishu", "qbot"],
        "download_security_version": 2,
    }
    cfg.update(nested)
    for k in list(cfg.keys()):
        if k in raw:
            cfg[k] = raw[k]
    return raw, cfg

def report_download_log_path():
    raw, _ = load_report_runtime()
    paths = raw.get("paths") if isinstance(raw.get("paths"), dict) else {}
    rel = paths.get("report_download_server_log", "orchestration/report_download_server_log.jsonl")
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def ensure_signing_key():
    data = load_json(OPENCLAW_SECRETS, {})
    report_download = data.get("report_download")
    if not isinstance(report_download, dict):
        report_download = {}
    key = report_download.get("signing_key")
    if not key:
        raise RuntimeError("missing report_download.signing_key in ~/.openclaw/secrets.json")
    return key

def sign_delivery_code(delivery_code, expires_ts):
    key = ensure_signing_key().encode("utf-8")
    msg = f"{delivery_code}:{expires_ts}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def build_public_download_url(delivery_code, expires_ts):
    _, cfg = load_report_runtime()
    base = cfg["public_download_base_url"].rstrip("/")
    return f"{base}/{delivery_code}?expires={expires_ts}&sig={sign_delivery_code(delivery_code, expires_ts)}"

def verify_signature(delivery_code, expires_ts, sig):
    expected = sign_delivery_code(delivery_code, expires_ts)
    return hmac.compare_digest(expected, sig)

def append_jsonl(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def artifact_kind_by_ext(ext):
    mapping = {
        ".docx": "word_report",
        ".xlsx": "excel_scoring",
        ".zip": "delivery_package",
        ".json": "download_manifest",
        ".pdf": "pdf_report",
    }
    return mapping.get(ext.lower(), ext.lower().lstrip(".") or "file")

def delivery_policy(file_ext):
    _, cfg = load_report_runtime()
    ext = (file_ext or "").lower()
    allowed = set(cfg.get("allowed_public_extensions", []))
    downloadable = ext in allowed
    ttl_hours = int(cfg.get("default_link_ttl_hours", 24))
    max_downloads = int(cfg.get("default_max_downloads", 3))

    if ext == ".zip":
        ttl_hours = int(cfg.get("package_link_ttl_hours", ttl_hours))
        max_downloads = int(cfg.get("package_max_downloads", max_downloads))
    elif ext == ".json":
        downloadable = bool(cfg.get("json_manifest_downloadable", False))
        ttl_hours = int(cfg.get("sensitive_link_ttl_hours", 2))
        max_downloads = 1

    return {
        "downloadable": downloadable,
        "ttl_hours": ttl_hours,
        "max_downloads": max_downloads,
    }

def expires_at_from_hours(hours):
    dt = utc_now() + timedelta(hours=int(hours))
    return dt, int(dt.timestamp())
