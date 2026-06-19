from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.lib.secret_refs import resolve_json_secret


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "insight_storage.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def resolve_db_cfg() -> dict[str, Any]:
    raw = load_json(CONFIG_PATH)
    selected = (
        raw.get("db")
        or raw.get("postgres")
        or raw.get("database")
        or ((raw.get("storage") or {}).get("db"))
        or ((raw.get("storage") or {}).get("postgres"))
        or ((raw.get("storage") or {}).get("database"))
        or {}
    )
    if not isinstance(selected, dict):
        raise ValueError("insight database configuration must be an object")
    db = dict(selected)
    if isinstance(db.get("password"), str) and db["password"].strip():
        raise RuntimeError("plaintext database password is forbidden")
    reference = db.get("password_secret_ref") or raw.get("password_secret_ref")
    if not isinstance(reference, str) or not reference.strip():
        raise RuntimeError("database password secret reference is missing")
    db["password"] = resolve_json_secret(reference)
    db.setdefault("sslmode", raw.get("sslmode", "disable"))
    return db


def _connection_parameters() -> dict[str, Any]:
    db = resolve_db_cfg()
    return {
        "host": db["host"],
        "port": db["port"],
        "dbname": db["dbname"],
        "user": db["user"],
        "password": db["password"],
        "sslmode": db.get("sslmode", "disable"),
    }


def db_connect():
    parameters = _connection_parameters()
    try:
        import psycopg2

        return psycopg2.connect(**parameters)
    except ModuleNotFoundError:
        import psycopg

        return psycopg.connect(**parameters)
