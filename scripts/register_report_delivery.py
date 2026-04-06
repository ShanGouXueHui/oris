#!/usr/bin/env python3
import json
from pathlib import Path

from lib.report_delivery_runtime import (
    ROOT,
    append_jsonl,
    artifact_kind_by_ext,
    build_public_download_url,
    db_connect,
    delivery_policy,
    ensure_signing_key,
    expires_at_from_hours,
    load_report_runtime,
    short_hash,
    slugify,
    utc_now,
)

OUTPUT_DIR = ROOT / "outputs" / "evals"

def delivery_code_for(channel, artifact_code):
    return f"delivery-{channel}-{slugify(artifact_code)}-{short_hash(channel + ':' + artifact_code)}"

def scan_files():
    if not OUTPUT_DIR.exists():
        return []
    files = []
    for p in sorted(OUTPUT_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in {".docx", ".xlsx", ".zip", ".json", ".pdf"}:
            files.append(p)
    return files

def ensure_artifact(cur, file_path):
    rel_path = str(file_path.relative_to(ROOT))
    title = file_path.name
    file_ext = file_path.suffix.lower()
    artifact_type = file_ext.lstrip(".")
    artifact_kind = artifact_kind_by_ext(file_ext)
    policy = delivery_policy(file_ext)
    file_size = file_path.stat().st_size
    artifact_code = f"artifact-{artifact_kind}-{slugify(file_path.stem)}-{short_hash(rel_path)}"

    cur.execute("""
        SET search_path TO insight,public;
        SELECT id, artifact_code
        FROM report_artifact
        WHERE storage_path = %s
        LIMIT 1
    """, (rel_path,))
    row = cur.fetchone()

    if row:
        artifact_id = row[0]
        cur.execute("""
            SET search_path TO insight,public;
            UPDATE report_artifact
            SET artifact_type = %s,
                title = %s,
                file_ext = %s,
                file_size = %s,
                downloadable_flag = %s,
                manifest_json = COALESCE(manifest_json, '{}'::jsonb)
            WHERE id = %s
        """, (
            artifact_type,
            title,
            file_ext,
            file_size,
            policy["downloadable"],
            artifact_id,
        ))
        return {
            "action": "existing",
            "artifact_id": artifact_id,
            "artifact_code": row[1],
            "file_path": rel_path,
            "file_ext": file_ext,
            "title": title,
        }

    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO report_artifact(
            artifact_code,
            artifact_type,
            title,
            storage_path,
            file_ext,
            file_size,
            manifest_json,
            downloadable_flag
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
        RETURNING id, artifact_code
    """, (
        artifact_code,
        artifact_type,
        title,
        rel_path,
        file_ext,
        file_size,
        json.dumps({}),
        policy["downloadable"],
    ))
    new_row = cur.fetchone()
    return {
        "action": "inserted",
        "artifact_id": new_row[0],
        "artifact_code": new_row[1],
        "file_path": rel_path,
        "file_ext": file_ext,
        "title": title,
    }

def ensure_delivery_task(cur, artifact, channel):
    policy = delivery_policy(artifact["file_ext"])
    if not policy["downloadable"]:
        return {
            "action": "skipped_not_downloadable",
            "channel": channel,
            "artifact_id": artifact["artifact_id"],
            "artifact_code": artifact["artifact_code"],
        }

    expires_at, expires_ts = expires_at_from_hours(policy["ttl_hours"])

    cur.execute("""
        SET search_path TO insight,public;
        SELECT id, delivery_code, used_count, max_downloads
        FROM delivery_task
        WHERE artifact_id = %s
          AND channel_type = %s
          AND status = 'pending'
          AND revoked_at IS NULL
        ORDER BY id DESC
        LIMIT 1
    """, (artifact["artifact_id"], channel))
    row = cur.fetchone()

    if row:
        delivery_task_id, delivery_code, used_count, max_downloads = row
        if not delivery_code:
            delivery_code = delivery_code_for(channel, artifact["artifact_code"])
        download_url = build_public_download_url(delivery_code, expires_ts)
        delivery_result_json = {
            "title": artifact["title"],
            "file_ext": artifact["file_ext"],
            "artifact_id": artifact["artifact_id"],
            "artifact_code": artifact["artifact_code"],
            "delivery_code": delivery_code,
            "channel_type": channel,
            "delivery_mode": "download_link",
            "download_url": download_url,
            "expires_at": expires_at.isoformat(),
            "expires_ts": expires_ts,
            "storage_path": artifact["file_path"],
        }
        cur.execute("""
            SET search_path TO insight,public;
            UPDATE delivery_task
            SET delivery_code = %s,
                delivery_mode = %s,
                download_url = %s,
                issued_at = now(),
                expires_at = %s,
                max_downloads = %s,
                status = 'pending',
                delivery_result_json = %s::jsonb
            WHERE id = %s
        """, (
            delivery_code,
            "download_link",
            download_url,
            expires_at,
            policy["max_downloads"],
            json.dumps(delivery_result_json, ensure_ascii=False),
            delivery_task_id,
        ))
        return {
            "action": "updated_existing",
            "delivery_task_id": delivery_task_id,
            "delivery_code": delivery_code,
            "channel": channel,
            "artifact_id": artifact["artifact_id"],
            "artifact_code": artifact["artifact_code"],
            "download_url": download_url,
        }

    delivery_code = delivery_code_for(channel, artifact["artifact_code"])
    download_url = build_public_download_url(delivery_code, expires_ts)
    delivery_result_json = {
        "title": artifact["title"],
        "file_ext": artifact["file_ext"],
        "artifact_id": artifact["artifact_id"],
        "artifact_code": artifact["artifact_code"],
        "delivery_code": delivery_code,
        "channel_type": channel,
        "delivery_mode": "download_link",
        "download_url": download_url,
        "expires_at": expires_at.isoformat(),
        "expires_ts": expires_ts,
        "storage_path": artifact["file_path"],
    }
    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO delivery_task(
            artifact_id,
            delivery_code,
            channel_type,
            channel_target,
            delivery_mode,
            status,
            max_downloads,
            used_count,
            issued_at,
            expires_at,
            download_url,
            delivery_result_json
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s,%s::jsonb)
        RETURNING id
    """, (
        artifact["artifact_id"],
        delivery_code,
        channel,
        channel_target_for(channel, runtime_cfg),
        "download_link",
        "pending",
        policy["max_downloads"],
        0,
        expires_at,
        download_url,
        json.dumps(delivery_result_json, ensure_ascii=False),
    ))
    delivery_task_id = cur.fetchone()[0]
    return {
        "action": "inserted",
        "delivery_task_id": delivery_task_id,
        "delivery_code": delivery_code,
        "channel": channel,
        "artifact_id": artifact["artifact_id"],
        "artifact_code": artifact["artifact_code"],
        "download_url": download_url,
    }


def channel_target_for(channel, runtime_cfg):
    delivery_cfg = runtime_cfg.get("delivery") if isinstance(runtime_cfg, dict) else {}
    targets = delivery_cfg.get("channel_targets") if isinstance(delivery_cfg, dict) else {}
    channels = runtime_cfg.get("channels") if isinstance(runtime_cfg, dict) else {}

    target_cfg = targets.get(channel) if isinstance(targets, dict) else None
    if isinstance(target_cfg, dict):
        target = target_cfg.get("default_target")
        if target:
            return target

    ch_cfg = channels.get(channel) if isinstance(channels, dict) else None
    if isinstance(ch_cfg, dict):
        target = ch_cfg.get("default_receive_id") or ch_cfg.get("default_target")
        if target:
            return target

    return None

def main():
    ensure_signing_key()
    runtime_cfg, report_cfg = load_report_runtime()
    channels = list(report_cfg.get("downloadable_channels", ["feishu", "qbot"]))
    files = scan_files()

    conn = db_connect()
    artifacts = []
    delivery_tasks = []
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SET search_path TO insight,public;
                    WITH ranked AS (
                      SELECT id,
                             ROW_NUMBER() OVER (
                               PARTITION BY artifact_id, channel_type
                               ORDER BY id DESC
                             ) AS rn
                      FROM delivery_task
                      WHERE status = 'pending'
                        AND revoked_at IS NULL
                    )
                    DELETE FROM delivery_task d
                    USING ranked r
                    WHERE d.id = r.id
                      AND r.rn > 1
                """)
                for file_path in files:
                    artifact = ensure_artifact(cur, file_path)
                    artifacts.append({
                        "action": artifact["action"],
                        "artifact_id": artifact["artifact_id"],
                        "artifact_code": artifact["artifact_code"],
                        "file_path": artifact["file_path"],
                    })
                    for channel in channels:
                        delivery_tasks.append(ensure_delivery_task(cur, artifact, channel))

                cur.execute("SET search_path TO insight,public; SELECT COUNT(*) FROM report_artifact")
                report_artifact_count = cur.fetchone()[0]
                cur.execute("SET search_path TO insight,public; SELECT COUNT(*) FROM delivery_task")
                delivery_task_count = cur.fetchone()[0]

                cur.execute("""
                    SET search_path TO insight,public;
                    SELECT id, artifact_code, title, storage_path, created_at
                    FROM report_artifact
                    ORDER BY id DESC
                    LIMIT 5
                """)
                latest_artifacts = [
                    {
                        "id": r[0],
                        "artifact_code": r[1],
                        "title": r[2],
                        "storage_path": r[3],
                        "created_at": str(r[4]),
                    }
                    for r in cur.fetchall()
                ]

                cur.execute("""
                    SET search_path TO insight,public;
                    SELECT id, artifact_id, delivery_code, channel_type, delivery_mode, status, created_at
                    FROM delivery_task
                    ORDER BY id DESC
                    LIMIT 10
                """)
                latest_delivery_tasks = [
                    {
                        "id": r[0],
                        "artifact_id": r[1],
                        "delivery_code": r[2],
                        "channel_type": r[3],
                        "delivery_mode": r[4],
                        "status": r[5],
                        "created_at": str(r[6]),
                    }
                    for r in cur.fetchall()
                ]
    finally:
        conn.close()

    print(json.dumps({
        "ok": True,
        "schema": "insight",
        "files_scanned": len(files),
        "artifacts": artifacts,
        "delivery_tasks": delivery_tasks,
        "report_artifact_count": report_artifact_count,
        "delivery_task_count": delivery_task_count,
        "latest_artifacts": latest_artifacts,
        "latest_delivery_tasks": latest_delivery_tasks,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
