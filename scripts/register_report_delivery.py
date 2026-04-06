#!/usr/bin/env python3
import hashlib
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor

ROOT = Path('/home/admin/projects/oris')
CONFIG_PATH = ROOT / 'config' / 'report_runtime.json'
STORAGE_PATH = ROOT / 'config' / 'insight_storage.json'
SECRETS_PATH = Path('/home/admin/.openclaw/secrets.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def deep_get(obj, path, default=None):
    cur = obj
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def first_value(obj, path_list, default=None):
    for path in path_list:
        value = deep_get(obj, path, None)
        if value is not None:
            return value
    return default


def read_db_config():
    storage = load_json(STORAGE_PATH)
    secrets = load_json(SECRETS_PATH)

    database_value = storage.get("database")
    if isinstance(database_value, str):
        dbname = database_value
    else:
        dbname = first_value(storage, [
            ["database", "name"],
            ["connection", "database"],
            ["connection", "dbname"],
            ["dbname"],
            ["name"],
        ], "oris_insight")

    host = first_value(storage, [
        ["host"],
        ["connection", "host"],
        ["database", "host"],
    ], "127.0.0.1")

    port = int(first_value(storage, [
        ["port"],
        ["connection", "port"],
        ["database", "port"],
    ], 5432))

    user = first_value(storage, [
        ["user"],
        ["connection", "user"],
        ["database", "user"],
    ], "oris_app")

    password = secrets["postgres"]["oris_insight"]["password"]
    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
    }


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_files(cfg):
    root_dir = ROOT / cfg["artifact_scan"]["root_dir"]
    patterns = cfg["artifact_scan"]["patterns"]
    max_files = int(cfg["artifact_scan"].get("max_files_per_run", 20))
    found = {}
    for pattern in patterns:
        for path in root_dir.glob(pattern):
            if path.is_file():
                found[str(path)] = path
    files = sorted(found.values(), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:max_files]


def get_columns(cur, schema, table):
    cur.execute(
        """
        SELECT
            column_name,
            is_nullable,
            column_default,
            data_type,
            udt_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )
    return cur.fetchall()


def choose_id_column(columns):
    names = [c["column_name"] for c in columns]
    for candidate in ["artifact_id", "delivery_task_id", "task_id", "id"]:
        if candidate in names:
            return candidate
    return None


def normalize_record_for_insert(columns, values):
    insert_values = {}
    missing_required = []

    for col in columns:
        name = col["column_name"]
        nullable = col["is_nullable"] == "YES"
        has_default = col["column_default"] is not None

        if name in values:
            insert_values[name] = values[name]
        elif not nullable and not has_default:
            missing_required.append(name)

    return insert_values, missing_required


def dynamic_insert(cur, schema, table, columns_meta, values):
    insert_values, missing_required = normalize_record_for_insert(columns_meta, values)
    if missing_required:
        raise RuntimeError(f"{table} missing required columns: {missing_required}")

    cols = list(insert_values.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f'INSERT INTO "{schema}"."{table}" ({", ".join(cols)}) VALUES ({placeholders}) RETURNING *'
    cur.execute(sql, [insert_values[c] for c in cols])
    return cur.fetchone()


def find_existing_artifact(cur, schema, table, columns_meta, artifact_values):
    names = {c["column_name"] for c in columns_meta}
    if "sha256" in names and "storage_path" in names:
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE sha256 = %s AND storage_path = %s ORDER BY 1 LIMIT 1',
            (artifact_values["sha256"], artifact_values["storage_path"]),
        )
        row = cur.fetchone()
        if row:
            return row
    if "file_name" in names and "storage_path" in names:
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE file_name = %s AND storage_path = %s ORDER BY 1 LIMIT 1',
            (artifact_values["file_name"], artifact_values["storage_path"]),
        )
        row = cur.fetchone()
        if row:
            return row
    return None


def find_existing_delivery(cur, schema, table, columns_meta, delivery_values):
    names = {c["column_name"] for c in columns_meta}
    if "artifact_id" in names and "channel" in names and "status" in names:
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE artifact_id = %s AND channel = %s AND status = %s ORDER BY 1 LIMIT 1',
            (delivery_values.get("artifact_id"), delivery_values.get("channel"), delivery_values.get("status")),
        )
        row = cur.fetchone()
        if row:
            return row
    if "artifact_id" in names and "target_channel" in names and "status" in names:
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE artifact_id = %s AND target_channel = %s AND status = %s ORDER BY 1 LIMIT 1',
            (delivery_values.get("artifact_id"), delivery_values.get("target_channel"), delivery_values.get("status")),
        )
        row = cur.fetchone()
        if row:
            return row
    return None


def build_artifact_values(cfg, file_path: Path):
    suffix = file_path.suffix.lower()
    rel_path = str(file_path.relative_to(ROOT))
    stat = file_path.stat()
    sha256 = sha256_file(file_path)
    mime_type = cfg["mime_type_map"].get(suffix) or mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    kind = cfg["artifact_kind_map"].get(suffix, "unknown_artifact")
    ts = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    metadata = {
        "artifact_kind": kind,
        "relative_path": rel_path,
        "generated_at": ts,
        "generator_name": cfg["source"]["generator_name"],
        "generator_type": cfg["source"]["generator_type"],
        "producer_channel": cfg["source"]["producer_channel"],
    }
    artifact_uuid = str(uuid.uuid4())

    return {
        "artifact_id": artifact_uuid,
        "id": artifact_uuid,
        "artifact_kind": kind,
        "artifact_type": suffix.lstrip("."),
        "artifact_name": file_path.name,
        "file_name": file_path.name,
        "file_ext": suffix,
        "mime_type": mime_type,
        "storage_path": rel_path,
        "download_path": rel_path,
        "artifact_uri": rel_path,
        "sha256": sha256,
        "size_bytes": stat.st_size,
        "file_size_bytes": stat.st_size,
        "status": "ready",
        "source_name": cfg["source"]["generator_name"],
        "source_type": cfg["source"]["generator_type"],
        "channel": cfg["source"]["producer_channel"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "metadata": Json(metadata),
        "meta_json": Json(metadata),
        "notes": "auto-registered from outputs/evals",
    }


def build_delivery_values(cfg, artifact_row, file_path: Path, channel: str):
    artifact_id = (
        artifact_row.get("artifact_id")
        or artifact_row.get("id")
    )
    task_uuid = str(uuid.uuid4())
    payload = {
        "channel": channel,
        "artifact_file_name": file_path.name,
        "artifact_relative_path": str(file_path.relative_to(ROOT)),
        "artifact_kind": artifact_row.get("artifact_kind") or artifact_row.get("artifact_type"),
        "downloadable": True,
    }
    status = cfg["delivery"]["default_status"]

    return {
        "delivery_task_id": task_uuid,
        "task_id": task_uuid,
        "id": task_uuid,
        "artifact_id": artifact_id,
        "task_type": cfg["delivery"]["task_type"],
        "channel": channel,
        "target_channel": channel,
        "status": status,
        "payload": Json(payload),
        "meta_json": Json(payload),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "notes": "auto-created delivery task from artifact registry",
    }


def main():
    cfg = load_json(CONFIG_PATH)
    db_cfg = read_db_config()
    schema = cfg["db"]["schema"]
    artifact_table = cfg["db"]["report_artifact_table"]
    delivery_table = cfg["db"]["delivery_task_table"]
    files = discover_files(cfg)

    if not files:
        raise SystemExit("no files found under outputs/evals")

    conn = psycopg2.connect(
        host=db_cfg["host"],
        port=db_cfg["port"],
        dbname=db_cfg["dbname"],
        user=db_cfg["user"],
        password=db_cfg["password"],
    )

    summary = {
        "db": {
            "host": db_cfg["host"],
            "port": db_cfg["port"],
            "dbname": db_cfg["dbname"],
            "user": db_cfg["user"],
            "schema": schema,
        },
        "files_scanned": len(files),
        "artifacts": [],
        "delivery_tasks": [],
    }

    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                artifact_columns = get_columns(cur, schema, artifact_table)
                delivery_columns = get_columns(cur, schema, delivery_table)

                for file_path in files:
                    artifact_values = build_artifact_values(cfg, file_path)
                    existing = find_existing_artifact(cur, schema, artifact_table, artifact_columns, artifact_values)
                    if existing:
                        artifact_row = existing
                        artifact_action = "existing"
                    else:
                        artifact_row = dynamic_insert(cur, schema, artifact_table, artifact_columns, artifact_values)
                        artifact_action = "inserted"

                    artifact_id = artifact_row.get("artifact_id") or artifact_row.get("id")
                    summary["artifacts"].append({
                        "action": artifact_action,
                        "artifact_id": artifact_id,
                        "file_name": file_path.name,
                        "storage_path": str(file_path.relative_to(ROOT)),
                    })

                    for channel in cfg["delivery"]["channels"]:
                        delivery_values = build_delivery_values(cfg, artifact_row, file_path, channel)
                        if not cfg["delivery"].get("allow_duplicate_pending_tasks", False):
                            existing_delivery = find_existing_delivery(cur, schema, delivery_table, delivery_columns, delivery_values)
                        else:
                            existing_delivery = None

                        if existing_delivery:
                            delivery_row = existing_delivery
                            delivery_action = "existing"
                        else:
                            delivery_row = dynamic_insert(cur, schema, delivery_table, delivery_columns, delivery_values)
                            delivery_action = "inserted"

                        delivery_id = (
                            delivery_row.get("delivery_task_id")
                            or delivery_row.get("task_id")
                            or delivery_row.get("id")
                        )
                        summary["delivery_tasks"].append({
                            "action": delivery_action,
                            "delivery_task_id": delivery_id,
                            "artifact_id": artifact_id,
                            "channel": channel,
                            "file_name": file_path.name,
                        })

                cur.execute(f'SELECT COUNT(*) AS cnt FROM "{schema}"."{artifact_table}"')
                summary["artifact_count"] = cur.fetchone()["cnt"]

                cur.execute(f'SELECT COUNT(*) AS cnt FROM "{schema}"."{delivery_table}"')
                summary["delivery_task_count"] = cur.fetchone()["cnt"]

        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
