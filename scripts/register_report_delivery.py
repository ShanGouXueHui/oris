#!/usr/bin/env python3
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor

ROOT = Path('/home/admin/projects/oris')
CONFIG_PATH = ROOT / 'config' / 'report_runtime.json'
STORAGE_PATH = ROOT / 'config' / 'insight_storage.json'
SECRETS_PATH = Path('/home/admin/.openclaw/secrets.json')


def utc_now_dt():
    return datetime.now(timezone.utc)


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

    database_value = storage.get('database')
    if isinstance(database_value, str):
        dbname = database_value
    else:
        dbname = first_value(storage, [
            ['database', 'name'],
            ['connection', 'database'],
            ['connection', 'dbname'],
            ['dbname'],
            ['name'],
        ], 'oris_insight')

    host = first_value(storage, [
        ['host'],
        ['connection', 'host'],
        ['database', 'host'],
    ], '127.0.0.1')

    port = int(first_value(storage, [
        ['port'],
        ['connection', 'port'],
        ['database', 'port'],
    ], 5432))

    user = first_value(storage, [
        ['user'],
        ['connection', 'user'],
        ['database', 'user'],
    ], 'oris_app')

    password = secrets['postgres']['oris_insight']['password']
    return {
        'host': host,
        'port': port,
        'dbname': dbname,
        'user': user,
        'password': password,
    }


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def discover_files(cfg):
    root_dir = ROOT / cfg['artifact_scan']['root_dir']
    patterns = cfg['artifact_scan']['patterns']
    max_files = int(cfg['artifact_scan'].get('max_files_per_run', 20))
    found = {}
    for pattern in patterns:
        for path in root_dir.glob(pattern):
            if path.is_file():
                found[str(path)] = path
    files = sorted(found.values(), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:max_files]


def get_columns(cur, schema, table):
    cur.execute(
        '''
        SELECT
            column_name,
            is_nullable,
            column_default,
            data_type,
            udt_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        ''',
        (schema, table),
    )
    return cur.fetchall()


def sanitize_token(text, max_len=120):
    value = re.sub(r'[^a-zA-Z0-9._-]+', '_', str(text)).strip('._-')
    value = re.sub(r'_+', '_', value)
    if not value:
        value = 'item'
    return value[:max_len]


def build_artifact_code(cfg, file_path: Path, artifact_kind: str, sha256: str):
    prefix = cfg.get('naming', {}).get('artifact_code_prefix', 'artifact')
    max_len = int(cfg.get('naming', {}).get('max_code_length', 120))
    stem = sanitize_token(file_path.stem, 64)
    kind = sanitize_token(artifact_kind, 32)
    code = f'{prefix}-{kind}-{stem}-{sha256[:8]}'
    return sanitize_token(code, max_len)


def build_delivery_code(cfg, file_path: Path, channel: str, artifact_code: str):
    prefix = cfg.get('naming', {}).get('delivery_code_prefix', 'delivery')
    max_len = int(cfg.get('naming', {}).get('max_code_length', 120))
    stem = sanitize_token(file_path.stem, 48)
    channel = sanitize_token(channel, 24)
    base = f'{prefix}-{channel}-{stem}-{artifact_code[-8:]}'
    return sanitize_token(base, max_len)


def candidate_artifact_values(cfg, file_path: Path):
    suffix = file_path.suffix.lower()
    rel_path = str(file_path.relative_to(ROOT))
    stat = file_path.stat()
    sha256 = sha256_file(file_path)
    artifact_kind = cfg['artifact_kind_map'].get(suffix, 'unknown_artifact')
    mime_type = cfg['mime_type_map'].get(suffix, 'application/octet-stream')
    generated_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    actor = cfg.get('defaults', {}).get('system_actor', 'system')
    artifact_code = build_artifact_code(cfg, file_path, artifact_kind, sha256)

    meta = {
        'artifact_kind': artifact_kind,
        'relative_path': rel_path,
        'generated_at': generated_at.isoformat(),
        'generator_name': cfg['source']['generator_name'],
        'generator_type': cfg['source']['generator_type'],
        'producer_channel': cfg['source']['producer_channel'],
    }

    return {
        'artifact_code': artifact_code,
        'report_code': artifact_code,
        'artifact_kind': artifact_kind,
        'artifact_type': suffix.lstrip('.'),
        'artifact_name': file_path.name,
        'title': file_path.name,
        'display_name': file_path.name,
        'name': file_path.name,
        'file_name': file_path.name,
        'file_ext': suffix,
        'mime_type': mime_type,
        'storage_path': rel_path,
        'download_path': rel_path,
        'artifact_uri': rel_path,
        'sha256': sha256,
        'size_bytes': stat.st_size,
        'file_size': stat.st_size,
        'file_size_bytes': stat.st_size,
        'status': 'ready',
        'source_name': cfg['source']['generator_name'],
        'source_type': cfg['source']['generator_type'],
        'channel': cfg['source']['producer_channel'],
        'producer_channel': cfg['source']['producer_channel'],
        'created_at': utc_now_dt(),
        'updated_at': utc_now_dt(),
        'generated_at': generated_at,
        'metadata': {'artifact_kind': artifact_kind, 'relative_path': rel_path},
        'meta_json': {'artifact_kind': artifact_kind, 'relative_path': rel_path},
        'notes': 'auto-registered from outputs/evals',
        'created_by': actor,
        'updated_by': actor,
        'version_num': int(cfg.get('defaults', {}).get('default_version_num', 1)),
        'version_no': int(cfg.get('defaults', {}).get('default_version_num', 1)),
        'is_active': bool(cfg.get('defaults', {}).get('default_is_active', True)),
        'is_deleted': bool(cfg.get('defaults', {}).get('default_is_deleted', False)),
        'deleted_flag': bool(cfg.get('defaults', {}).get('default_is_deleted', False)),
    }


def candidate_delivery_values(cfg, artifact_row, file_path: Path, channel: str):
    actor = cfg.get('defaults', {}).get('system_actor', 'system')
    artifact_id = artifact_row.get('artifact_id')
    if artifact_id is None:
        artifact_id = artifact_row.get('id')
    if artifact_id is None:
        artifact_id = artifact_row.get('report_artifact_id')

    artifact_code = artifact_row.get('artifact_code') or artifact_row.get('report_code') or 'artifact'
    delivery_code = build_delivery_code(cfg, file_path, channel, artifact_code)
    status = cfg['delivery']['default_status']
    payload = {
        'channel': channel,
        'artifact_file_name': file_path.name,
        'artifact_relative_path': str(file_path.relative_to(ROOT)),
        'downloadable': True,
        'delivery_mode': 'download',
    }

    return {
        'artifact_id': artifact_id,
        'report_artifact_id': artifact_id,
        'task_code': delivery_code,
        'delivery_code': delivery_code,
        'task_type': cfg['delivery']['task_type'],
        'delivery_type': cfg['delivery']['task_type'],
        'channel': channel,
        'target_channel': channel,
        'status': status,
        'payload': payload,
        'meta_json': payload,
        'created_at': utc_now_dt(),
        'updated_at': utc_now_dt(),
        'queued_at': utc_now_dt(),
        'notes': 'auto-created delivery task from artifact registry',
        'created_by': actor,
        'updated_by': actor,
        'priority': int(cfg.get('defaults', {}).get('default_priority', 100)),
        'retry_count': int(cfg.get('defaults', {}).get('default_retry_count', 0)),
        'attempt_count': int(cfg.get('defaults', {}).get('default_retry_count', 0)),
        'version_num': int(cfg.get('defaults', {}).get('default_version_num', 1)),
        'version_no': int(cfg.get('defaults', {}).get('default_version_num', 1)),
        'is_active': bool(cfg.get('defaults', {}).get('default_is_active', True)),
        'is_deleted': bool(cfg.get('defaults', {}).get('default_is_deleted', False)),
        'deleted_flag': bool(cfg.get('defaults', {}).get('default_is_deleted', False)),
    }


def maybe_uuid(value):
    try:
        return str(uuid.UUID(str(value)))
    except Exception:
        return None


def coerce_value(col, value):
    data_type = (col.get('data_type') or '').lower()
    udt_name = (col.get('udt_name') or '').lower()

    if value is None:
        return False, None

    if isinstance(value, Json):
        return True, value

    if data_type in {'json', 'jsonb'} or udt_name in {'json', 'jsonb'}:
        return True, Json(value)

    if data_type in {'bigint', 'integer', 'smallint'}:
        if isinstance(value, bool):
            return True, int(value)
        if isinstance(value, int):
            return True, value
        if isinstance(value, str) and re.fullmatch(r'-?\d+', value.strip()):
            return True, int(value.strip())
        return False, None

    if data_type == 'uuid':
        parsed = maybe_uuid(value)
        if parsed:
            return True, parsed
        return False, None

    if data_type == 'boolean':
        if isinstance(value, bool):
            return True, value
        if isinstance(value, int):
            return True, bool(value)
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {'true', 't', '1', 'yes', 'y'}:
                return True, True
            if v in {'false', 'f', '0', 'no', 'n'}:
                return True, False
        return False, None

    if data_type.startswith('timestamp') or data_type == 'date':
        if isinstance(value, datetime):
            return True, value
        if isinstance(value, str):
            return True, value
        return False, None

    if data_type in {'text', 'character varying', 'character'}:
        return True, str(value)

    return True, value


def synthesize_missing_values(table_name, columns_meta, values, cfg, file_path=None, artifact_code=None):
    values = dict(values)

    for col in columns_meta:
        name = col['column_name']
        nullable = col['is_nullable'] == 'YES'
        has_default = col['column_default'] is not None
        data_type = (col.get('data_type') or '').lower()
        udt_name = (col.get('udt_name') or '').lower()

        if name in values:
            ok, coerced = coerce_value(col, values[name])
            if ok:
                values[name] = coerced
                continue
            del values[name]

        if nullable or has_default:
            continue

        if name in {'created_at', 'updated_at', 'queued_at', 'generated_at'}:
            values[name] = utc_now_dt()
            continue

        if name in {'created_by', 'updated_by', 'actor', 'operator'}:
            values[name] = cfg.get('defaults', {}).get('system_actor', 'system')
            continue

        if name in {'version_num', 'version_no'}:
            values[name] = int(cfg.get('defaults', {}).get('default_version_num', 1))
            continue

        if name == 'priority':
            values[name] = int(cfg.get('defaults', {}).get('default_priority', 100))
            continue

        if name in {'retry_count', 'attempt_count', 'fail_count'}:
            values[name] = int(cfg.get('defaults', {}).get('default_retry_count', 0))
            continue

        if name in {'is_active', 'active', 'enabled'}:
            values[name] = bool(cfg.get('defaults', {}).get('default_is_active', True))
            continue

        if name in {'is_deleted', 'deleted_flag', 'deleted'}:
            values[name] = bool(cfg.get('defaults', {}).get('default_is_deleted', False))
            continue

        if name == 'status':
            values[name] = 'ready' if table_name == 'report_artifact' else cfg['delivery']['default_status']
            continue

        if name in {'metadata', 'meta_json', 'payload', 'context_json', 'extra_json'} and (data_type in {'json', 'jsonb'} or udt_name in {'json', 'jsonb'}):
            values[name] = Json({})
            continue

        if name in {'source_name'}:
            values[name] = cfg['source']['generator_name']
            continue

        if name in {'source_type'}:
            values[name] = cfg['source']['generator_type']
            continue

        if name in {'channel', 'producer_channel'} and table_name == 'report_artifact':
            values[name] = cfg['source']['producer_channel']
            continue

        if name in {'task_type', 'delivery_type'} and table_name == 'delivery_task':
            values[name] = cfg['delivery']['task_type']
            continue

        if name in {'artifact_code', 'report_code'} and file_path is not None:
            sha256 = values.get('sha256', 'unknownsha')
            artifact_kind = values.get('artifact_kind', 'artifact')
            values[name] = build_artifact_code(cfg, file_path, artifact_kind, sha256)
            continue

        if name in {'task_code', 'delivery_code'} and file_path is not None:
            channel = values.get('channel') or values.get('target_channel') or 'channel'
            ac = artifact_code or values.get('artifact_code') or 'artifact'
            values[name] = build_delivery_code(cfg, file_path, channel, ac)
            continue

        if data_type == 'uuid':
            values[name] = str(uuid.uuid4())
            continue

        if data_type in {'json', 'jsonb'} or udt_name in {'json', 'jsonb'}:
            values[name] = Json({})
            continue

        if data_type == 'boolean':
            values[name] = False
            continue

        if data_type.startswith('timestamp') or data_type == 'date':
            values[name] = utc_now_dt()
            continue

    return values


def normalize_record_for_insert(table_name, columns_meta, values, cfg, file_path=None, artifact_code=None):
    values = synthesize_missing_values(table_name, columns_meta, values, cfg, file_path=file_path, artifact_code=artifact_code)
    insert_values = {}
    missing_required = []

    for col in columns_meta:
        name = col['column_name']
        nullable = col['is_nullable'] == 'YES'
        has_default = col['column_default'] is not None

        if name in values:
            ok, coerced = coerce_value(col, values[name])
            if ok:
                insert_values[name] = coerced
            elif not nullable and not has_default:
                missing_required.append(name)
        elif not nullable and not has_default:
            missing_required.append(name)

    return insert_values, missing_required


def dynamic_insert(cur, schema, table, columns_meta, values, cfg, file_path=None, artifact_code=None):
    insert_values, missing_required = normalize_record_for_insert(
        table,
        columns_meta,
        values,
        cfg,
        file_path=file_path,
        artifact_code=artifact_code,
    )
    if missing_required:
        raise RuntimeError(f'{table} missing required columns after type-aware normalization: {missing_required}')

    cols = list(insert_values.keys())
    placeholders = ', '.join(['%s'] * len(cols))
    sql = f'INSERT INTO "{schema}"."{table}" ({", ".join(cols)}) VALUES ({placeholders}) RETURNING *'
    cur.execute(sql, [insert_values[c] for c in cols])
    return cur.fetchone()


def find_existing_artifact(cur, schema, table, columns_meta, values):
    names = {c['column_name'] for c in columns_meta}

    if 'artifact_code' in names and values.get('artifact_code'):
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE artifact_code = %s LIMIT 1',
            (values['artifact_code'],),
        )
        row = cur.fetchone()
        if row:
            return row

    if 'storage_path' in names and 'sha256' in names and values.get('storage_path') and values.get('sha256'):
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE storage_path = %s AND sha256 = %s LIMIT 1',
            (values['storage_path'], values['sha256']),
        )
        row = cur.fetchone()
        if row:
            return row

    return None


def find_existing_delivery(cur, schema, table, columns_meta, values):
    names = {c['column_name'] for c in columns_meta}

    if 'task_code' in names and values.get('task_code'):
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE task_code = %s LIMIT 1',
            (values['task_code'],),
        )
        row = cur.fetchone()
        if row:
            return row

    if 'delivery_code' in names and values.get('delivery_code'):
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE delivery_code = %s LIMIT 1',
            (values['delivery_code'],),
        )
        row = cur.fetchone()
        if row:
            return row

    candidate_artifact_col = 'artifact_id' if 'artifact_id' in names else ('report_artifact_id' if 'report_artifact_id' in names else None)
    candidate_channel_col = 'channel' if 'channel' in names else ('target_channel' if 'target_channel' in names else None)

    if candidate_artifact_col and candidate_channel_col and values.get(candidate_artifact_col) is not None and values.get(candidate_channel_col):
        cur.execute(
            f'SELECT * FROM "{schema}"."{table}" WHERE {candidate_artifact_col} = %s AND {candidate_channel_col} = %s LIMIT 1',
            (values[candidate_artifact_col], values[candidate_channel_col]),
        )
        row = cur.fetchone()
        if row:
            return row

    return None


def pretty_row(row, preferred_columns):
    result = {}
    for col in preferred_columns:
        if col in row:
            result[col] = row[col]
    return result


def main():
    cfg = load_json(CONFIG_PATH)
    db_cfg = read_db_config()
    schema = cfg['db']['schema']
    artifact_table = cfg['db']['report_artifact_table']
    delivery_table = cfg['db']['delivery_task_table']
    files = discover_files(cfg)

    if not files:
        raise SystemExit('no files found under outputs/evals')

    conn = psycopg2.connect(
        host=db_cfg['host'],
        port=db_cfg['port'],
        dbname=db_cfg['dbname'],
        user=db_cfg['user'],
        password=db_cfg['password'],
    )

    summary = {
        'db': db_cfg,
        'schema': schema,
        'files_scanned': len(files),
        'artifacts': [],
        'delivery_tasks': [],
    }

    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                artifact_columns = get_columns(cur, schema, artifact_table)
                delivery_columns = get_columns(cur, schema, delivery_table)

                for file_path in files:
                    artifact_values = candidate_artifact_values(cfg, file_path)
                    existing_artifact = find_existing_artifact(cur, schema, artifact_table, artifact_columns, artifact_values)

                    if existing_artifact:
                        artifact_row = existing_artifact
                        artifact_action = 'existing'
                    else:
                        artifact_row = dynamic_insert(
                            cur, schema, artifact_table, artifact_columns, artifact_values, cfg, file_path=file_path
                        )
                        artifact_action = 'inserted'

                    artifact_id = artifact_row.get('artifact_id')
                    if artifact_id is None:
                        artifact_id = artifact_row.get('id')
                    if artifact_id is None:
                        artifact_id = artifact_row.get('report_artifact_id')

                    artifact_code = artifact_row.get('artifact_code') or artifact_row.get('report_code')

                    summary['artifacts'].append({
                        'action': artifact_action,
                        'artifact_id': artifact_id,
                        'artifact_code': artifact_code,
                        'file_path': str(file_path.relative_to(ROOT)),
                    })

                    for channel in cfg['delivery']['channels']:
                        delivery_values = candidate_delivery_values(cfg, artifact_row, file_path, channel)
                        existing_delivery = None
                        if not cfg['delivery'].get('allow_duplicate_pending_tasks', False):
                            existing_delivery = find_existing_delivery(cur, schema, delivery_table, delivery_columns, delivery_values)

                        if existing_delivery:
                            delivery_row = existing_delivery
                            delivery_action = 'existing'
                        else:
                            delivery_row = dynamic_insert(
                                cur,
                                schema,
                                delivery_table,
                                delivery_columns,
                                delivery_values,
                                cfg,
                                file_path=file_path,
                                artifact_code=artifact_code,
                            )
                            delivery_action = 'inserted'

                        delivery_id = delivery_row.get('delivery_task_id')
                        if delivery_id is None:
                            delivery_id = delivery_row.get('task_id')
                        if delivery_id is None:
                            delivery_id = delivery_row.get('id')

                        delivery_code = delivery_row.get('task_code') or delivery_row.get('delivery_code')

                        summary['delivery_tasks'].append({
                            'action': delivery_action,
                            'delivery_task_id': delivery_id,
                            'delivery_code': delivery_code,
                            'channel': channel,
                            'artifact_id': artifact_id,
                        })

                cur.execute(f'SELECT COUNT(*) AS cnt FROM "{schema}"."{artifact_table}"')
                summary['report_artifact_count'] = cur.fetchone()['cnt']

                cur.execute(f'SELECT COUNT(*) AS cnt FROM "{schema}"."{delivery_table}"')
                summary['delivery_task_count'] = cur.fetchone()['cnt']

                cur.execute(f'SELECT * FROM "{schema}"."{artifact_table}" ORDER BY 1 DESC LIMIT 5')
                summary['latest_artifacts'] = [
                    pretty_row(row, ['id', 'artifact_id', 'artifact_code', 'report_code', 'title', 'name', 'storage_path', 'status', 'created_at'])
                    for row in cur.fetchall()
                ]

                cur.execute(f'SELECT * FROM "{schema}"."{delivery_table}" ORDER BY 1 DESC LIMIT 10')
                summary['latest_delivery_tasks'] = [
                    pretty_row(row, ['id', 'task_id', 'delivery_task_id', 'task_code', 'delivery_code', 'channel', 'target_channel', 'status', 'created_at'])
                    for row in cur.fetchall()
                ]

        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
