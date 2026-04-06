#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    p = Path(path)
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def db_cfg():
    cfg = load_json("config/insight_storage.json")
    db = (
        cfg.get("db")
        or cfg.get("postgres")
        or cfg.get("database")
        or (cfg.get("storage") or {}).get("db")
        or (cfg.get("storage") or {}).get("postgres")
        or (cfg.get("storage") or {}).get("database")
        or {}
    )

    password = db.get("password")
    if not password:
        sec = load_json("/home/admin/.openclaw/secrets.json")
        password = (((sec.get("postgres") or {}).get("oris_insight") or {}).get("password"))

    return {
        "host": db.get("host", "127.0.0.1"),
        "port": db.get("port", 5432),
        "dbname": db.get("dbname") or db.get("database") or db.get("name"),
        "user": db.get("user"),
        "password": password,
    }


def db_connect():
    dbc = db_cfg()
    return psycopg2.connect(
        host=dbc["host"],
        port=dbc["port"],
        dbname=dbc["dbname"],
        user=dbc["user"],
        password=dbc["password"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def runtime_cfg():
    return load_json("config/report_runtime.json")


def delivery_cfg():
    return (runtime_cfg().get("delivery") or {})


def channels_cfg():
    return (runtime_cfg().get("channels") or {})


def default_target(channel):
    dcfg = delivery_cfg()
    ccfg = channels_cfg()

    target_cfg = (dcfg.get("channel_targets") or {}).get(channel) or {}
    target = target_cfg.get("default_target")
    if target:
        return target

    ch = ccfg.get(channel) or {}
    target = ch.get("default_receive_id") or ch.get("default_target")
    if target:
        return target

    return None


def append_result_patch(existing, patch):
    base = existing if isinstance(existing, dict) else {}
    merged = dict(base)
    merged["executor"] = patch
    return merged


def build_text(row):
    result = row.get("delivery_result_json") or {}
    title = result.get("title") or f"artifact_{row.get('artifact_id')}"
    download_url = row.get("download_url") or result.get("download_url")
    delivery_code = row.get("delivery_code") or result.get("delivery_code")

    lines = [f"报告已生成：{title}"]
    if download_url:
        lines.append(download_url)
    if delivery_code:
        lines.append(f"delivery_code: {delivery_code}")
    return "\n".join(lines)


def feishu_preview_json(task_id, chat_id, text):
    return {
        "ok": True,
        "mode": "transport_preview",
        "identity": {
            "task_id": task_id,
            "channel": "feishu",
            "chat_id": chat_id,
        },
        "dedupe_key": f"delivery_task:{task_id}",
        "send_envelope": {
            "send_mode": "feishu_messages_api_preview",
            "endpoint_hint": "/open-apis/im/v1/messages",
            "receive_id_type": "chat_id",
            "receive_id": chat_id,
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
    }


def feishu_send(task_id, chat_id, text, execute):
    cmd = [
        "/usr/bin/python3",
        "scripts/feishu_send_executor_skeleton.py",
        "--transport-preview-json",
        json.dumps(feishu_preview_json(task_id, chat_id, text), ensure_ascii=False),
    ]
    if execute:
        cmd.append("--execute")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if not stdout:
        return {
            "ok": False,
            "mode": "feishu_send_empty_output",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }

    try:
        data = json.loads(stdout)
    except Exception as e:
        return {
            "ok": False,
            "mode": "feishu_send_non_json",
            "error": str(e),
            "stdout": stdout[:1000],
            "stderr": stderr[:1000],
            "returncode": result.returncode,
        }

    if result.returncode != 0:
        return {
            "ok": False,
            "mode": "feishu_send_failed",
            "data": data,
            "stderr": stderr[:1000],
            "returncode": result.returncode,
        }

    return {
        "ok": bool(data.get("ok")),
        "mode": data.get("mode"),
        "data": data,
    }


def qbot_webhook_url():
    ccfg = channels_cfg().get("qbot") or {}
    env_name = ccfg.get("webhook_url_env") or "QBOT_WEBHOOK_URL"
    return os.environ.get(env_name) or ccfg.get("webhook_url")


def qbot_send(task_id, target, text, execute):
    url = target if target and str(target).startswith("http") else qbot_webhook_url()
    if not url:
        return {
            "ok": False,
            "mode": "qbot_transport_not_configured",
            "error": "missing qbot webhook url",
        }

    payload = {"content": text}

    if not execute:
        return {
            "ok": True,
            "mode": "dry_run",
            "request_url": url,
            "request_payload": payload,
        }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "oris-delivery-executor/1.0",
            "X-ORIS-Delivery-Task-ID": str(task_id),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read(4000).decode("utf-8", "replace")
            return {
                "ok": 200 <= resp.getcode() < 300,
                "mode": "executed",
                "status_code": resp.getcode(),
                "response_body": body,
            }
    except urllib.error.HTTPError as e:
        try:
            body = e.read(4000).decode("utf-8", "replace")
        except Exception:
            body = str(e)
        return {
            "ok": False,
            "mode": "http_error",
            "status_code": e.code,
            "response_body": body,
        }
    except Exception as e:
        return {
            "ok": False,
            "mode": "exception",
            "error": str(e),
        }


def select_one_pending(cur, status, only_channel=None):
    sql = """
    SELECT
      id,
      artifact_id,
      channel_type,
      channel_target,
      delivery_mode,
      status,
      delivery_result_json,
      created_at,
      delivered_at,
      delivery_code,
      max_downloads,
      used_count,
      expires_at,
      issued_at,
      last_downloaded_at,
      revoked_at,
      revoke_reason,
      download_url
    FROM insight.delivery_task
    WHERE status = %s
    """
    params = [status]

    if only_channel:
        sql += " AND channel_type = %s"
        params.append(only_channel)

    sql += """
    ORDER BY created_at, id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
    """
    cur.execute(sql, params)
    return cur.fetchone()


def patch_task(cur, row, status, target_used, executor_patch, mark_delivered):
    patch_json = append_result_patch(row.get("delivery_result_json") or {}, executor_patch)

    if mark_delivered:
        cur.execute("""
            UPDATE insight.delivery_task
               SET status = %s,
                   channel_target = COALESCE(channel_target, %s),
                   delivered_at = COALESCE(delivered_at, now()),
                   delivery_result_json = %s::jsonb
             WHERE id = %s
        """, (
            status,
            target_used,
            json.dumps(patch_json, ensure_ascii=False),
            row["id"],
        ))
    else:
        cur.execute("""
            UPDATE insight.delivery_task
               SET status = %s,
                   channel_target = COALESCE(channel_target, %s),
                   delivery_result_json = %s::jsonb
             WHERE id = %s
        """, (
            status,
            target_used,
            json.dumps(patch_json, ensure_ascii=False),
            row["id"],
        ))


def handle_task(row, execute):
    channel = (row.get("channel_type") or "").strip().lower()
    target = row.get("channel_target") or default_target(channel)
    mode = row.get("delivery_mode")
    text = build_text(row)

    if row.get("revoked_at"):
        return False, target, {
            "ts": utc_now(),
            "ok": False,
            "reason": "revoked",
            "revoke_reason": row.get("revoke_reason"),
        }

    if row.get("expires_at") and datetime.now(timezone.utc) > row["expires_at"].astimezone(timezone.utc):
        return False, target, {
            "ts": utc_now(),
            "ok": False,
            "reason": "expired",
            "expires_at": row["expires_at"].isoformat(),
        }

    if mode != "download_link":
        return False, target, {
            "ts": utc_now(),
            "ok": False,
            "reason": "unsupported_delivery_mode",
            "delivery_mode": mode,
        }

    if channel == "feishu":
        if not target:
            return False, target, {
                "ts": utc_now(),
                "ok": False,
                "reason": "channel_target_missing",
                "channel": channel,
            }
        resp = feishu_send(row["id"], target, text, execute)
        return bool(resp.get("ok")), target, {
            "ts": utc_now(),
            "ok": bool(resp.get("ok")),
            "channel": channel,
            "target_used": target,
            "send_mode": resp.get("mode"),
            "send_result": resp,
        }

    if channel == "qbot":
        resp = qbot_send(row["id"], target, text, execute)
        return bool(resp.get("ok")), target, {
            "ts": utc_now(),
            "ok": bool(resp.get("ok")),
            "channel": channel,
            "target_used": target,
            "send_mode": resp.get("mode"),
            "send_result": resp,
        }

    return False, target, {
        "ts": utc_now(),
        "ok": False,
        "reason": "unsupported_channel",
        "channel": channel,
    }


def probe():
    print(json.dumps({
        "delivery": delivery_cfg(),
        "channels": channels_cfg(),
    }, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--max-tasks", type=int, default=20)
    ap.add_argument("--poll-seconds", type=int, default=10)
    ap.add_argument("--only-channel", default=None)
    args = ap.parse_args()

    if args.probe:
        probe()
        return

    dcfg = delivery_cfg()
    pending_status = dcfg.get("pending_status", "pending")
    sent_status = dcfg.get("sent_status", "sent")
    failed_status = dcfg.get("failed_status", "failed")

    conn = db_connect()
    conn.autocommit = False

    try:
        while True:
            processed = 0
            while processed < args.max_tasks:
                with conn.cursor() as cur:
                    row = select_one_pending(cur, pending_status, args.only_channel)
                    if not row:
                        conn.rollback()
                        break

                    ok, target_used, executor_patch = handle_task(row, execute=(not args.dry_run))
                    patch_task(
                        cur=cur,
                        row=row,
                        status=(sent_status if ok else failed_status),
                        target_used=target_used,
                        executor_patch=executor_patch,
                        mark_delivered=ok,
                    )

                    if args.dry_run:
                        conn.rollback()
                    else:
                        conn.commit()

                    print(json.dumps({
                        "task_id": row["id"],
                        "channel": row.get("channel_type"),
                        "target_used": target_used,
                        "status": sent_status if ok else failed_status,
                        "dry_run": bool(args.dry_run),
                        "executor_patch": executor_patch,
                    }, ensure_ascii=False))

                    processed += 1

                if args.dry_run:
                    break

            if args.once:
                break

            import time
            time.sleep(args.poll_seconds)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
