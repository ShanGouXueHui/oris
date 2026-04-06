#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.report_delivery_runtime import db_connect, load_report_runtime, build_public_download_url

SCAN_ROOT = ROOT / "outputs" / "report_build"

def utc_now():
    return datetime.now(timezone.utc)

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def rel_str(path: Path) -> str:
    return str(path.relative_to(ROOT))

def artifact_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".docx":
        return "word_report"
    if ext == ".xlsx":
        return "excel_report"
    if ext == ".pptx":
        return "ppt_report"
    if ext == ".pdf":
        return "pdf_report"
    if ext == ".zip":
        return "delivery_package"
    if ext == ".json":
        return "report_json"
    return "file"

def downloadable_flag_for(path: Path, report_cfg: dict) -> bool:
    allowed = set((report_cfg.get("allowed_public_extensions") or []))
    return path.suffix.lower() in allowed

def artifact_code_for(path: Path, artifact_type: str) -> str:
    stem = path.stem.lower().replace(" ", "_")
    digest = hashlib.md5(rel_str(path).encode("utf-8")).hexdigest()[:8]
    return f"artifact-{artifact_type}-{stem}-{digest}"

def delivery_code_for(channel: str, artifact_code: str) -> str:
    digest = hashlib.md5(f"{channel}:{artifact_code}".encode("utf-8")).hexdigest()[:8]
    return f"delivery-{channel}-{artifact_code}-{digest}"

def channels_for(runtime_cfg: dict, report_cfg: dict):
    delivery_cfg = runtime_cfg.get("delivery") or {}
    execution_channels = list(delivery_cfg.get("execution_channels") or [])
    if execution_channels:
        return execution_channels
    return list(report_cfg.get("downloadable_channels") or ["feishu", "qbot"])

def channel_target_for(channel: str, runtime_cfg: dict):
    delivery_cfg = runtime_cfg.get("delivery") or {}
    channels_cfg = runtime_cfg.get("channels") or {}

    targets = delivery_cfg.get("channel_targets") or {}
    target_cfg = targets.get(channel) or {}
    ch_cfg = channels_cfg.get(channel) or {}

    return (
        target_cfg.get("default_target")
        or ch_cfg.get("default_receive_id")
        or ch_cfg.get("default_target")
    )

def scan_files():
    if not SCAN_ROOT.exists():
        return []
    out = []
    for path in sorted(SCAN_ROOT.rglob("*")):
        if path.is_file():
            out.append(path)
    return out

def find_existing_artifact(cur, storage_path: str):
    cur.execute("""
        SET search_path TO insight,public;
        SELECT id, artifact_code
        FROM report_artifact
        WHERE storage_path = %s
        ORDER BY id DESC
        LIMIT 1
    """, (storage_path,))
    row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "artifact_code": row[1]}

def upsert_artifact(cur, path: Path, report_cfg: dict, dry_run: bool):
    storage_path = rel_str(path)
    title = path.name
    file_ext = path.suffix.lower()
    file_size = path.stat().st_size
    artifact_type = artifact_type_for(path)
    downloadable_flag = downloadable_flag_for(path, report_cfg)
    artifact_code = artifact_code_for(path, artifact_type)

    manifest_json = {
        "source": "report_build_skill",
        "storage_path": storage_path,
        "title": title,
        "file_ext": file_ext,
        "file_size": file_size,
        "artifact_type": artifact_type,
        "downloadable_flag": downloadable_flag,
    }

    existing = find_existing_artifact(cur, storage_path)
    if existing:
        if not dry_run:
            cur.execute("""
                SET search_path TO insight,public;
                UPDATE report_artifact
                SET
                    artifact_type = %s,
                    title = %s,
                    file_ext = %s,
                    file_size = %s,
                    downloadable_flag = %s,
                    manifest_json = %s::jsonb
                WHERE id = %s
            """, (
                artifact_type,
                title,
                file_ext,
                file_size,
                downloadable_flag,
                json.dumps(manifest_json, ensure_ascii=False),
                existing["id"],
            ))
        return {
            "action": "updated_existing",
            "artifact_id": existing["id"],
            "artifact_code": existing["artifact_code"],
            "storage_path": storage_path,
            "artifact_type": artifact_type,
            "downloadable_flag": downloadable_flag,
        }

    if dry_run:
        return {
            "action": "would_insert",
            "artifact_id": None,
            "artifact_code": artifact_code,
            "storage_path": storage_path,
            "artifact_type": artifact_type,
            "downloadable_flag": downloadable_flag,
        }

    cur.execute("""
        SET search_path TO insight,public;
        INSERT INTO report_artifact(
            artifact_code,
            run_id,
            request_id,
            artifact_type,
            title,
            storage_path,
            file_ext,
            file_size,
            manifest_json,
            downloadable_flag
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
        RETURNING id
    """, (
        artifact_code,
        None,
        None,
        artifact_type,
        title,
        storage_path,
        file_ext,
        file_size,
        json.dumps(manifest_json, ensure_ascii=False),
        downloadable_flag,
    ))
    artifact_id = cur.fetchone()[0]
    return {
        "action": "inserted",
        "artifact_id": artifact_id,
        "artifact_code": artifact_code,
        "storage_path": storage_path,
        "artifact_type": artifact_type,
        "downloadable_flag": downloadable_flag,
    }

def find_existing_delivery(cur, artifact_id: int, channel: str):
    cur.execute("""
        SET search_path TO insight,public;
        SELECT id, delivery_code, status
        FROM delivery_task
        WHERE artifact_id = %s AND channel_type = %s
        ORDER BY id DESC
        LIMIT 1
    """, (artifact_id, channel))
    row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "delivery_code": row[1], "status": row[2]}

def ensure_delivery(cur, artifact: dict, path: Path, runtime_cfg: dict, report_cfg: dict, dry_run: bool):
    if not artifact.get("downloadable_flag"):
        return []

    delivery_cfg = runtime_cfg.get("delivery") or {}
    ttl_hours = int(report_cfg.get("default_link_ttl_hours") or 24)
    max_downloads = int(report_cfg.get("default_max_downloads") or 3)

    channels = channels_for(runtime_cfg, report_cfg)
    out = []

    for channel in channels:
        target = channel_target_for(channel, runtime_cfg)
        existing = None
        if artifact.get("artifact_id") is not None:
            existing = find_existing_delivery(cur, artifact["artifact_id"], channel)

        delivery_code = existing["delivery_code"] if existing else delivery_code_for(channel, artifact["artifact_code"])
        expires_at = utc_now() + timedelta(hours=ttl_hours)
        expires_ts = int(expires_at.timestamp())
        download_url = build_public_download_url(delivery_code, expires_ts)

        delivery_result_json = {
            "title": path.name,
            "file_ext": path.suffix.lower(),
            "artifact_code": artifact["artifact_code"],
            "channel_type": channel,
            "delivery_mode": "download_link",
            "download_url": download_url,
            "expires_at": expires_at.isoformat(),
            "expires_ts": expires_ts,
            "storage_path": rel_str(path),
            "source": "register_report_build_delivery",
        }

        if existing:
            out.append({
                "action": "existing",
                "delivery_task_id": existing["id"],
                "channel": channel,
                "status": existing["status"],
                "delivery_code": delivery_code,
                "target": target,
                "download_url": download_url,
            })
            continue

        if dry_run:
            out.append({
                "action": "would_insert",
                "delivery_task_id": None,
                "channel": channel,
                "status": "pending",
                "delivery_code": delivery_code,
                "target": target,
                "download_url": download_url,
            })
            continue

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
            target,
            "download_link",
            delivery_cfg.get("pending_status", "pending"),
            max_downloads,
            0,
            expires_at,
            download_url,
            json.dumps(delivery_result_json, ensure_ascii=False),
        ))
        delivery_task_id = cur.fetchone()[0]
        out.append({
            "action": "inserted",
            "delivery_task_id": delivery_task_id,
            "channel": channel,
            "status": delivery_cfg.get("pending_status", "pending"),
            "delivery_code": delivery_code,
            "target": target,
            "download_url": download_url,
        })

    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    runtime_cfg, report_cfg = load_report_runtime()
    files = scan_files()

    result = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "scan_root": str(SCAN_ROOT),
        "file_count": len(files),
        "files": [],
    }

    conn = db_connect()
    try:
        with conn:
            with conn.cursor() as cur:
                for path in files:
                    artifact = upsert_artifact(cur, path, report_cfg, dry_run=args.dry_run)
                    deliveries = ensure_delivery(cur, artifact, path, runtime_cfg, report_cfg, dry_run=args.dry_run)
                    result["files"].append({
                        "path": rel_str(path),
                        "artifact": artifact,
                        "deliveries": deliveries,
                    })
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
