#!/usr/bin/env python3
import argparse
import json

from lib.report_delivery_runtime import db_connect

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delivery-code", required=False)
    ap.add_argument("--artifact-code", required=False)
    ap.add_argument("--reason", default="manual_revoke")
    args = ap.parse_args()

    if not args.delivery_code and not args.artifact_code:
        raise SystemExit("must provide --delivery-code or --artifact-code")

    conn = db_connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO insight,public;")
                if args.delivery_code:
                    cur.execute("""
                        UPDATE delivery_task
                        SET revoked_at = now(),
                            revoke_reason = %s,
                            status = 'revoked'
                        WHERE delivery_code = %s
                    """, (args.reason, args.delivery_code))
                else:
                    cur.execute("""
                        UPDATE delivery_task dt
                        SET revoked_at = now(),
                            revoke_reason = %s,
                            status = 'revoked'
                        FROM report_artifact ra
                        WHERE dt.artifact_id = ra.id
                          AND ra.artifact_code = %s
                    """, (args.reason, args.artifact_code))
                print(json.dumps({
                    "ok": True,
                    "updated_rows": cur.rowcount,
                    "reason": args.reason,
                    "delivery_code": args.delivery_code,
                    "artifact_code": args.artifact_code,
                }, ensure_ascii=False, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
