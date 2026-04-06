#!/usr/bin/env python3
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import psycopg2.extras

from lib.report_delivery_runtime import (
    ROOT,
    append_jsonl,
    db_connect,
    load_report_runtime,
    report_download_log_path,
    utc_now,
    verify_signature,
)

RAW_RUNTIME, REPORT_CFG = load_report_runtime()
HOST = "127.0.0.1"
PORT = 8791
DOWNLOAD_PATH_PREFIX = REPORT_CFG.get("download_path_prefix", "/download")
HEALTH_PATH = "/health"
LOG_PATH = report_download_log_path()

def json_response(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        return

def file_response(handler, file_path, download_name):
    ctype, _ = mimetypes.guess_type(str(file_path))
    if not ctype:
        ctype = "application/octet-stream"
    body = Path(file_path).read_bytes()
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        return

def load_delivery(delivery_code):
    conn = db_connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SET search_path TO insight,public;
                    SELECT
                      dt.id AS delivery_task_id,
                      dt.artifact_id,
                      dt.delivery_code,
                      dt.channel_type,
                      dt.delivery_mode,
                      dt.status,
                      dt.max_downloads,
                      dt.used_count,
                      dt.expires_at,
                      dt.revoked_at,
                      dt.download_url,
                      ra.artifact_code,
                      ra.title,
                      ra.storage_path,
                      ra.file_ext,
                      ra.downloadable_flag
                    FROM delivery_task dt
                    JOIN report_artifact ra ON ra.id = dt.artifact_id
                    WHERE dt.delivery_code = %s
                    LIMIT 1
                """, (delivery_code,))
                return cur.fetchone()
    finally:
        conn.close()

def record_event_and_mark(row, client_ip, user_agent, path, query, status, detail_json):
    conn = db_connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO insight,public;")
                cur.execute("""
                    INSERT INTO download_event(
                      artifact_id,
                      delivery_task_id,
                      artifact_code,
                      delivery_code,
                      channel_type,
                      client_ip,
                      user_agent,
                      request_path,
                      request_query,
                      status,
                      detail_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                """, (
                    row.get("artifact_id"),
                    row.get("delivery_task_id"),
                    row.get("artifact_code"),
                    row.get("delivery_code"),
                    row.get("channel_type"),
                    client_ip,
                    user_agent,
                    path,
                    query,
                    status,
                    json.dumps(detail_json, ensure_ascii=False),
                ))
                if status == "success":
                    cur.execute("""
                        UPDATE delivery_task
                        SET used_count = COALESCE(used_count, 0) + 1,
                            last_downloaded_at = now(),
                            delivered_at = COALESCE(delivered_at, now()),
                            status = CASE
                              WHEN COALESCE(used_count, 0) + 1 >= COALESCE(max_downloads, 999999) THEN 'downloaded'
                              ELSE status
                            END
                        WHERE id = %s
                    """, (row["delivery_task_id"],))
    finally:
        conn.close()

class Handler(BaseHTTPRequestHandler):
    server_version = "ORISReportDownload/2.0"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parsed.query

        if path == HEALTH_PATH:
            json_response(self, 200, {
                "ok": True,
                "service": "oris-report-download-server",
                "listen": f"http://{HOST}:{PORT}",
                "download_path_prefix": DOWNLOAD_PATH_PREFIX,
                "security_model": "signed_delivery_code_v2",
            })
            return

        if not path.startswith(DOWNLOAD_PATH_PREFIX + "/"):
            json_response(self, 404, {"ok": False, "error": "not_found"})
            return

        delivery_code = path.split("/")[-1]
        params = parse_qs(query)
        expires = (params.get("expires") or [None])[0]
        sig = (params.get("sig") or [None])[0]
        client_ip = self.headers.get("X-Real-IP") or self.client_address[0]
        user_agent = self.headers.get("User-Agent", "")

        if not delivery_code or not expires or not sig:
            json_response(self, 400, {"ok": False, "error": "missing_signature_params"})
            return

        row = load_delivery(delivery_code)
        if not row:
            json_response(self, 404, {"ok": False, "error": "not_found"})
            return

        try:
            expires_ts = int(expires)
        except Exception:
            record_event_and_mark(row, client_ip, user_agent, path, query, "blocked_bad_expires", {})
            json_response(self, 400, {"ok": False, "error": "bad_expires"})
            return

        now_ts = int(utc_now().timestamp())
        if expires_ts < now_ts:
            record_event_and_mark(row, client_ip, user_agent, path, query, "blocked_expired", {"expires_ts": expires_ts, "now_ts": now_ts})
            json_response(self, 403, {"ok": False, "error": "expired"})
            return

        if not verify_signature(delivery_code, expires_ts, sig):
            record_event_and_mark(row, client_ip, user_agent, path, query, "blocked_bad_signature", {})
            json_response(self, 403, {"ok": False, "error": "bad_signature"})
            return

        if row.get("revoked_at"):
            record_event_and_mark(row, client_ip, user_agent, path, query, "blocked_revoked", {})
            json_response(self, 403, {"ok": False, "error": "revoked"})
            return

        if not row.get("downloadable_flag"):
            record_event_and_mark(row, client_ip, user_agent, path, query, "blocked_not_downloadable", {})
            json_response(self, 403, {"ok": False, "error": "not_downloadable"})
            return

        used_count = row.get("used_count") or 0
        max_downloads = row.get("max_downloads") or 3
        if used_count >= max_downloads:
            record_event_and_mark(row, client_ip, user_agent, path, query, "blocked_max_downloads", {
                "used_count": used_count,
                "max_downloads": max_downloads,
            })
            json_response(self, 403, {"ok": False, "error": "max_downloads_exceeded"})
            return

        file_path = ROOT / row["storage_path"]
        if not file_path.exists():
            record_event_and_mark(row, client_ip, user_agent, path, query, "blocked_file_missing", {
                "storage_path": row["storage_path"],
            })
            json_response(self, 404, {"ok": False, "error": "file_missing"})
            return

        append_jsonl(LOG_PATH, {
            "ts": utc_now().isoformat(),
            "ok": True,
            "mode": "download_success",
            "delivery_code": row["delivery_code"],
            "artifact_code": row["artifact_code"],
            "channel_type": row["channel_type"],
            "client_ip": client_ip,
            "path": path,
        })
        record_event_and_mark(row, client_ip, user_agent, path, query, "success", {
            "storage_path": row["storage_path"],
            "title": row["title"],
        })
        file_response(self, file_path, row["title"])

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    append_jsonl(LOG_PATH, {
        "ts": utc_now().isoformat(),
        "ok": True,
        "mode": "startup",
        "service": "oris-report-download-server",
        "listen": f"http://{HOST}:{PORT}",
        "download_path_prefix": DOWNLOAD_PATH_PREFIX,
        "security_model": "signed_delivery_code_v2",
    })
    print(json.dumps({
        "ok": True,
        "service": "oris-report-download-server",
        "listen": f"http://{HOST}:{PORT}",
        "download_path_prefix": DOWNLOAD_PATH_PREFIX,
        "security_model": "signed_delivery_code_v2",
    }, ensure_ascii=False))
    server.serve_forever()

if __name__ == "__main__":
    main()
