#!/usr/bin/env python3
import hmac
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path('/home/admin/projects/oris')
REPORT_CFG_PATH = ROOT / 'config' / 'report_runtime.json'
STORAGE_CFG_PATH = ROOT / 'config' / 'insight_storage.json'
SECRETS_PATH = Path('/home/admin/.openclaw/secrets.json')

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

REPORT_CFG = read_json(REPORT_CFG_PATH)
STORAGE_CFG = read_json(STORAGE_CFG_PATH)
SECRETS_CFG = read_json(SECRETS_PATH)

def first_value(obj, paths, default=None):
    for path in paths:
        cur = obj
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and cur is not None:
            return cur
    return default

def db_conn_kwargs():
    database_value = STORAGE_CFG.get('database')
    if isinstance(database_value, str):
        dbname = database_value
    else:
        dbname = first_value(STORAGE_CFG, [['database', 'name'], ['connection', 'database'], ['connection', 'dbname'], ['dbname']], 'oris_insight')

    return {
        'host': first_value(STORAGE_CFG, [['host'], ['connection', 'host'], ['database', 'host']], '127.0.0.1'),
        'port': int(first_value(STORAGE_CFG, [['port'], ['connection', 'port'], ['database', 'port']], 5432)),
        'dbname': dbname,
        'user': first_value(STORAGE_CFG, [['user'], ['connection', 'user'], ['database', 'user']], 'oris_app'),
        'password': (((SECRETS_CFG.get('postgres') or {}).get('oris_insight') or {}).get('password')),
    }

DB_SCHEMA = ((REPORT_CFG.get('db') or {}).get('schema')) or 'insight'
ARTIFACT_TABLE = ((REPORT_CFG.get('db') or {}).get('report_artifact_table')) or 'report_artifact'
DELIVERY_TABLE = ((REPORT_CFG.get('db') or {}).get('delivery_task_table')) or 'delivery_task'

DOWNLOAD_CFG = REPORT_CFG.get('download') or {}
PUBLIC_BASE_URL = DOWNLOAD_CFG.get('public_base_url', 'https://control.orisfy.com').rstrip('/')
PUBLIC_PATH_PREFIX = DOWNLOAD_CFG.get('public_path_prefix', '/oris-download').rstrip('/')
LINK_TTL_SECONDS = int(DOWNLOAD_CFG.get('link_ttl_seconds', 604800))
DEFAULT_DELIVERY_MODE = ((REPORT_CFG.get('delivery') or {}).get('default_delivery_mode')) or 'download_link'
SIGNING_KEY = (((SECRETS_CFG.get('report_delivery') or {}).get('download_signing_key')) or '').encode('utf-8')

def build_signature(artifact_code: str, expires: str) -> str:
    msg = f'{artifact_code}:{expires}'.encode('utf-8')
    return hmac.new(SIGNING_KEY, msg, hashlib.sha256).hexdigest()

def build_download_url(artifact_code: str):
    expires_dt = datetime.now(timezone.utc) + timedelta(seconds=LINK_TTL_SECONDS)
    expires_ts = str(int(expires_dt.timestamp()))
    sig = build_signature(artifact_code, expires_ts)
    url = f'{PUBLIC_BASE_URL}{PUBLIC_PATH_PREFIX}/{artifact_code}?expires={expires_ts}&sig={sig}'
    return {
        'download_url': url,
        'expires_at': expires_dt.isoformat(),
        'expires_ts': int(expires_ts),
    }

def main():
    conn = psycopg2.connect(**db_conn_kwargs())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f'''
                SELECT
                    dt.id AS delivery_task_id,
                    dt.channel_type,
                    dt.status,
                    dt.delivery_mode,
                    dt.delivery_result_json,
                    ra.id AS artifact_id,
                    ra.artifact_code,
                    ra.title,
                    ra.storage_path,
                    ra.file_ext
                FROM "{DB_SCHEMA}"."{DELIVERY_TABLE}" dt
                JOIN "{DB_SCHEMA}"."{ARTIFACT_TABLE}" ra
                  ON ra.id = dt.artifact_id
                WHERE dt.status = 'pending'
                ORDER BY dt.id ASC
            ''')
            rows = cur.fetchall()

            updated = []
            for row in rows:
                link_info = build_download_url(row['artifact_code'])
                result_json = row.get('delivery_result_json') or {}
                result_json.update({
                    'artifact_id': row['artifact_id'],
                    'artifact_code': row['artifact_code'],
                    'title': row['title'],
                    'storage_path': row['storage_path'],
                    'file_ext': row['file_ext'],
                    'channel_type': row['channel_type'],
                    'delivery_mode': DEFAULT_DELIVERY_MODE,
                    **link_info,
                })

                cur.execute(f'''
                    UPDATE "{DB_SCHEMA}"."{DELIVERY_TABLE}"
                    SET delivery_mode = %s,
                        delivery_result_json = %s
                    WHERE id = %s
                ''', [DEFAULT_DELIVERY_MODE, json.dumps(result_json, ensure_ascii=False), row['delivery_task_id']])

                updated.append({
                    'delivery_task_id': row['delivery_task_id'],
                    'artifact_code': row['artifact_code'],
                    'channel_type': row['channel_type'],
                    'delivery_mode': DEFAULT_DELIVERY_MODE,
                    'download_url': link_info['download_url'],
                    'expires_at': link_info['expires_at'],
                })

            conn.commit()
            print(json.dumps({
                'ok': True,
                'updated_count': len(updated),
                'updated_tasks': updated[:20],
            }, ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == '__main__':
    main()
