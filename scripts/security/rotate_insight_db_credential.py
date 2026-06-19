from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path
from typing import Any

from scripts.lib.secret_refs import resolve_json_secret, set_json_secret


CONFIG_RELATIVE_PATH = Path("config/insight_storage.json")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("insight storage config must contain a JSON object")
    return value


def _connection_parameters(config: dict[str, Any], password: str) -> dict[str, Any]:
    db = config.get("db")
    if not isinstance(db, dict):
        raise ValueError("insight storage config has no db object")
    required = ("host", "port", "dbname", "user")
    if any(key not in db for key in required):
        raise ValueError("insight database config is incomplete")
    return {
        "host": db["host"],
        "port": db["port"],
        "dbname": db["dbname"],
        "user": db["user"],
        "password": password,
        "connect_timeout": 10,
        "sslmode": config.get("sslmode", "disable"),
    }


def _connect(parameters: dict[str, Any]):
    try:
        import psycopg2

        return psycopg2.connect(**parameters), "psycopg2"
    except ModuleNotFoundError:
        import psycopg

        return psycopg.connect(**parameters), "psycopg"


def _alter_role_password(connection, driver: str, role: str, password: str) -> None:
    if driver == "psycopg2":
        from psycopg2 import sql
    else:
        from psycopg import sql
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("ALTER ROLE {} PASSWORD %s").format(sql.Identifier(role)),
            (password,),
        )


def _verify_connection(config: dict[str, Any], password: str) -> None:
    connection, _ = _connect(_connection_parameters(config, password))
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if not row or row[0] != 1:
                raise RuntimeError("database verification query failed")
    finally:
        connection.close()


def rotate(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / CONFIG_RELATIVE_PATH
    config = _load_json(config_path)
    db = config.get("db")
    if not isinstance(db, dict):
        raise ValueError("insight storage db config is missing")
    if "password" in config or "password" in db:
        raise RuntimeError("plaintext database password remains in tracked config")
    reference = db.get("password_secret_ref") or config.get("password_secret_ref")
    if not isinstance(reference, str) or not reference:
        raise RuntimeError("database password secret reference is missing")

    old_password = resolve_json_secret(reference)
    new_password = secrets.token_urlsafe(48)
    role = str(db["user"])
    connection, driver = _connect(_connection_parameters(config, old_password))
    secret_file_updated = False
    try:
        _alter_role_password(connection, driver, role, new_password)
        set_json_secret(reference, new_password)
        secret_file_updated = True
        connection.commit()
        try:
            _verify_connection(config, new_password)
        except Exception:
            _alter_role_password(connection, driver, role, old_password)
            connection.commit()
            set_json_secret(reference, old_password)
            secret_file_updated = False
            raise
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        if secret_file_updated:
            try:
                set_json_secret(reference, old_password)
            except Exception:
                pass
        raise
    finally:
        connection.close()

    return {
        "result": "ROTATED_AND_VERIFIED",
        "config_path": CONFIG_RELATIVE_PATH.as_posix(),
        "plaintext_password_present": False,
        "secret_reference_used": True,
        "database_connection_verified": True,
        "old_secret_recorded": False,
        "new_secret_recorded": False,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("result JSON path argument is required", file=sys.stderr)
        return 64
    repo_root = Path(__file__).resolve().parents[2]
    result_path = Path(sys.argv[1]).expanduser().resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = rotate(repo_root)
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        result_path.write_text(
            json.dumps(
                {
                    "result": "FAILED",
                    "failure_type": type(exc).__name__,
                    "plaintext_secret_values_recorded": False,
                },
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
