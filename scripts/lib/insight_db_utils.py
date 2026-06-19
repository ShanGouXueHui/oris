from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def utc_now():
    return datetime.now(timezone.utc)


def slugify(text: str, default: str = "item") -> str:
    value = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower())
    value = value.strip("-")
    return value or default


def sha1_text(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def root_domain(url: str) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.strip().lower()
    return host or None


def build_insert_sql(
    table_name: str,
    data: dict,
    returning: str = "id",
):
    keys = list(data.keys())
    placeholders: list[str] = []
    values: list[object] = []
    for key in keys:
        if key.endswith("_json"):
            placeholders.append("%s::jsonb")
            values.append(json.dumps(data[key], ensure_ascii=False))
        else:
            placeholders.append("%s")
            values.append(data[key])
    columns = ", ".join(keys)
    parameters = ", ".join(placeholders)
    sql = f"INSERT INTO {table_name}({columns}) VALUES ({parameters}) RETURNING {returning}"
    return sql, values
