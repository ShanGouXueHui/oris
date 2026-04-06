#!/usr/bin/env python3
import hmac
import json
import mimetypes
import hashlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

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

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def rel_path(key: str) -> Path:
    rel = (((REPORT_CFG.get('paths') or {}).get(key)) or '')
    if not rel:
        raise RuntimeError(f'missing report_runtime.paths.{key}')
    return ROOT / rel

LOG_PATH = rel_path('report_download_log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def append_jsonl(path: Path, record: dict):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

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

def json_response(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    try:
        handler.send_response(code)
        handler.send_header('Content-Type', 'application/json; charset=utf-8')
        handler.send_header('Content-Length', str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        return

DOWNLOAD_CFG = REPORT_CFG.get('download') or {}
HOST = DOWNLOAD_CFG.get('bind_host', '127.0.0.1')
PORT = int(DOWNLOAD_CFG.get('bind_port', 8791))
HEALTH_PATH = DOWNLOAD_CFG.get('health_path', '/health')
DOWNLOAD_PATH_PREFIX = DOWNLOAD_CFG.get('download_path_prefix', '/download')
DB_SCHEMA = ((REPORT_CFG.get('db') or {}).get('schema')) or 'insight'
ARTIFACT_TABLE = ((REPORT_CFG.get('db') or {}).get('report_artifact_table')) or 'report_artifact'
SIGNING_KEY = (((SECRETS_CFG.get('report_delivery') or {}).get('download_signing_key')) or '').encode('utf-8')

def build_signature(artifact_code: str, expires: str) -> str:
    msg = f'{artifact_code}:{expires}'.encode('utf-8')
    return hmac.new(SIGNING_KEY, msg, hashlib.sha256).hexdigest()

def fetch_artifact_by_code(artifact_code: str):
    sql = f'''
        SELECT id, artifact_code, title, storage_path, file_ext, file_size, downloadable_flag, created_at
        FROM "{DB_SCHEMA}"."{ARTIFACT_TABLE}"
        WHERE artifact_code = %s
        LIMIT 1
    '''
    conn = psycopg2.connect(**db_conn_kwargs())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [artifact_code])
            return cur.fetchone()
    finally:
        conn.close()

class Handler(BaseHTTPRequestHandler):
    server_version = 'ORISReportDownload/1.0'

    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)

        if path == HEALTH_PATH:
            json_response(self, 200, {
                'ok': True,
                'service': 'oris-report-download-server',
                'listen': f'http://{HOST}:{PORT}',
                'download_path_prefix': DOWNLOAD_PATH_PREFIX,
            })
            return

        if not path.startswith(DOWNLOAD_PATH_PREFIX + '/'):
            append_jsonl(LOG_PATH, {
                'ts': utc_now(),
                'ok': False,
                'mode': 'not_found',
                'path': path,
            })
            json_response(self, 404, {'ok': False, 'error': 'not_found'})
            return

        artifact_code = unquote(path[len(DOWNLOAD_PATH_PREFIX) + 1:])
        expires = (qs.get('expires') or [''])[0]
        sig = (qs.get('sig') or [''])[0]

        if not artifact_code or not expires or not sig:
            append_jsonl(LOG_PATH, {
                'ts': utc_now(),
                'ok': False,
                'mode': 'missing_params',
                'artifact_code': artifact_code,
                'path': path,
            })
            json_response(self, 400, {'ok': False, 'error': 'missing_params'})
            return

        try:
            expires_int = int(expires)
        except Exception:
            json_response(self, 400, {'ok': False, 'error': 'invalid_expires'})
            return

        now_ts = int(datetime.now(timezone.utc).timestamp())
        if expires_int < now_ts:
            json_response(self, 410, {'ok': False, 'error': 'link_expired'})
            return

        expected_sig = build_signature(artifact_code, expires)
        if not hmac.compare_digest(expected_sig, sig):
            append_jsonl(LOG_PATH, {
                'ts': utc_now(),
                'ok': False,
                'mode': 'bad_signature',
                'artifact_code': artifact_code,
            })
            json_response(self, 403, {'ok': False, 'error': 'bad_signature'})
            return

        artifact = fetch_artifact_by_code(artifact_code)
        if not artifact:
            json_response(self, 404, {'ok': False, 'error': 'artifact_not_found'})
            return

        if not artifact.get('downloadable_flag'):
            json_response(self, 403, {'ok': False, 'error': 'artifact_not_downloadable'})
            return

        file_path = ROOT / artifact['storage_path']
        if not file_path.exists() or not file_path.is_file():
            json_response(self, 404, {'ok': False, 'error': 'file_missing'})
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'

        filename = artifact.get('title') or file_path.name
        try:
            file_size = file_path.stat().st_size
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            with file_path.open('rb') as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            append_jsonl(LOG_PATH, {
                'ts': utc_now(),
                'ok': True,
                'mode': 'download_served',
                'artifact_code': artifact_code,
                'storage_path': artifact['storage_path'],
                'file_size': file_size,
            })
        except (BrokenPipeError, ConnectionResetError):
            append_jsonl(LOG_PATH, {
                'ts': utc_now(),
                'ok': True,
                'mode': 'download_client_closed',
                'artifact_code': artifact_code,
            })
            return

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(json.dumps({
        'ok': True,
        'service': 'oris-report-download-server',
        'listen': f'http://{HOST}:{PORT}',
        'download_path_prefix': DOWNLOAD_PATH_PREFIX,
    }, ensure_ascii=False))
    server.serve_forever()

if __name__ == '__main__':
    main()
