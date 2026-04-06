#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.report_delivery_runtime import db_connect


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis-run-id", type=int, required=True)
    ap.add_argument("--source-snapshot-id", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = db_connect()
    out = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "analysis_run_id": args.analysis_run_id,
        "source_snapshot_id": args.source_snapshot_id,
        "inserted": [],
        "skipped_existing": [],
    }

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO insight,public;")

                cur.execute("""
                    SELECT id, run_code, request_id, target_company_id
                    FROM analysis_run
                    WHERE id = %s
                """, (args.analysis_run_id,))
                run = cur.fetchone()
                if not run:
                    raise RuntimeError(f"analysis_run not found: {args.analysis_run_id}")
                _, run_code, request_id, target_company_id = run

                cur.execute("""
                    SELECT id, source_id, company_id, snapshot_title, snapshot_url
                    FROM source_snapshot
                    WHERE id = %s
                """, (args.source_snapshot_id,))
                snap = cur.fetchone()
                if not snap:
                    raise RuntimeError(f"source_snapshot not found: {args.source_snapshot_id}")
                snapshot_id, source_id, company_id, snapshot_title, snapshot_url = snap

                if target_company_id != company_id:
                    raise RuntimeError(
                        f"company mismatch: analysis_run.company={target_company_id}, snapshot.company={company_id}"
                    )

                cur.execute("""
                    SELECT id, evidence_title
                    FROM evidence_item
                    WHERE source_snapshot_id = %s
                    ORDER BY id ASC
                """, (snapshot_id,))
                evidence_rows = cur.fetchall()

                for evidence_id, evidence_title in evidence_rows:
                    claim_code = f"{run_code}:snapshot_{snapshot_id}:evidence_{evidence_id}"
                    citation_label = evidence_title or f"{snapshot_title} / evidence {evidence_id}"
                    citation_note = "auto_backfill_from_ingest"

                    cur.execute("""
                        SELECT id
                        FROM citation_link
                        WHERE claim_code = %s
                           OR (evidence_item_id = %s AND source_snapshot_id = %s)
                        ORDER BY id ASC
                        LIMIT 1
                    """, (claim_code, evidence_id, snapshot_id))
                    existing = cur.fetchone()

                    item = {
                        "claim_code": claim_code,
                        "evidence_item_id": evidence_id,
                        "source_snapshot_id": snapshot_id,
                        "source_id": source_id,
                        "citation_label": citation_label,
                        "citation_url": snapshot_url,
                    }

                    if existing:
                        item["citation_id"] = existing[0]
                        out["skipped_existing"].append(item)
                        continue

                    if args.dry_run:
                        out["inserted"].append(item)
                        continue

                    cur.execute("""
                        INSERT INTO citation_link(
                            request_id,
                            report_id,
                            claim_code,
                            evidence_item_id,
                            source_snapshot_id,
                            source_id,
                            citation_label,
                            citation_url,
                            citation_note
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING id
                    """, (
                        request_id,
                        None,
                        claim_code,
                        evidence_id,
                        snapshot_id,
                        source_id,
                        citation_label,
                        snapshot_url,
                        citation_note,
                    ))
                    item["citation_id"] = cur.fetchone()[0]
                    out["inserted"].append(item)

        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
