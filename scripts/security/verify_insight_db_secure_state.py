from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from scripts.lib.insight_db import db_connect


EVIDENCE_DIRECTORY = Path("logs/dev_employee/security_remediation")
SUCCESS_RESULTS = {"ROTATED_AND_VERIFIED", "ALREADY_SECURE_AND_VERIFIED"}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("security evidence must contain a JSON object")
    return value


def _latest_successful_evidence(repo_root: Path) -> Path | None:
    directory = repo_root / EVIDENCE_DIRECTORY
    for path in sorted(
        directory.glob("insight-db-credential-rotation-*.json"),
        reverse=True,
    ):
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if payload.get("result") in SUCCESS_RESULTS:
            return path
    return None


def verify(repo_root: Path) -> dict[str, Any]:
    evidence = _latest_successful_evidence(repo_root)
    if evidence is None:
        return {
            "result": "ROTATION_REQUIRED",
            "successful_evidence_present": False,
            "database_connection_verified": False,
            "credential_rotated_this_run": False,
            "secret_values_recorded": False,
        }

    connection = db_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        verified = bool(row and row[0] == 1)
    finally:
        connection.close()
    return {
        "result": (
            "ALREADY_SECURE_AND_VERIFIED"
            if verified
            else "ROTATION_REQUIRED"
        ),
        "successful_evidence_present": True,
        "database_connection_verified": verified,
        "credential_rotated_this_run": False,
        "secret_values_recorded": False,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("result JSON path argument is required", file=sys.stderr)
        return 64
    repo_root = Path(__file__).resolve().parents[2]
    result_path = Path(sys.argv[1]).expanduser().resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = verify(repo_root)
    except Exception as exc:
        result = {
            "result": "ROTATION_REQUIRED",
            "failure_type": type(exc).__name__,
            "successful_evidence_present": True,
            "database_connection_verified": False,
            "credential_rotated_this_run": False,
            "secret_values_recorded": False,
        }
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
