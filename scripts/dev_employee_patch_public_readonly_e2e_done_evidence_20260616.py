#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path("/home/admin/projects/oris/scripts/dev_employee_run_public_readonly_e2e_final_20260616.py")

OLD_FUNCTION = '''def evidence_ready(payload: dict[str, Any]) -> bool:
    evidence = payload.get("github_evidence") if isinstance(payload.get("github_evidence"), dict) else {}
    files = evidence.get("files") if isinstance(evidence.get("files"), list) else []
    labels = {str(item.get("label")) for item in files if isinstance(item, dict)}
    return bool(
        evidence.get("product_commit_sha")
        and evidence.get("product_remote_sha")
        and evidence.get("oris_evidence_commit_sha")
        and evidence.get("evidence_index_commit_sha")
        and evidence.get("strict_result_schema") is True
        and "host_pytest_log" in labels
    )
'''

NEW_FUNCTION = '''def completed_done_record(payload: dict[str, Any]) -> dict[str, Any]:
    queue = payload.get("queue") if isinstance(payload.get("queue"), list) else []
    for item in queue:
        if not isinstance(item, dict) or item.get("suffix") != "done":
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        index_result = data.get("oris_evidence_index_result") if isinstance(data.get("oris_evidence_index_result"), dict) else {}
        if data.get("status") == "completed" and index_result.get("ok") and index_result.get("commit_sha"):
            return data
    return {}


def evidence_ready(payload: dict[str, Any]) -> bool:
    evidence = payload.get("github_evidence") if isinstance(payload.get("github_evidence"), dict) else {}
    files = evidence.get("files") if isinstance(evidence.get("files"), list) else []
    labels = {str(item.get("label")) for item in files if isinstance(item, dict)}
    return bool(
        evidence.get("product_commit_sha")
        and evidence.get("product_remote_sha")
        and evidence.get("oris_evidence_commit_sha")
        and evidence.get("strict_result_schema") is True
        and "host_pytest_log" in labels
        and completed_done_record(payload)
    )
'''

OLD_EXTRACTION = '''        state["ORIS_EVIDENCE_INDEX_COMMIT_SHA"] = str(evidence.get("evidence_index_commit_sha") or "")
        state["STRICT_RESULT_SCHEMA"] = "PASS" if evidence.get("strict_result_schema") is True else "FAILED"
'''

NEW_EXTRACTION = '''        done_data = completed_done_record(status_payload)
        index_result = done_data.get("oris_evidence_index_result") if isinstance(done_data.get("oris_evidence_index_result"), dict) else {}
        state["ORIS_EVIDENCE_INDEX_COMMIT_SHA"] = str(index_result.get("commit_sha") or "")
        state["STRICT_RESULT_SCHEMA"] = "PASS" if evidence.get("strict_result_schema") is True else "FAILED"
'''

OLD_USERNAME_ANCHOR = '''def env_value(key: str) -> str:
    if not ENV_FILE.is_file():
        return ""
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def public_request(
'''

NEW_USERNAME_ANCHOR = '''def env_value(key: str) -> str:
    if not ENV_FILE.is_file():
        return ""
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def basic_auth_username() -> str:
    nginx_conf = Path("/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf")
    if not nginx_conf.is_file():
        raise RuntimeError("public_basic_auth_nginx_config_missing")
    auth_file = ""
    for raw in nginx_conf.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#") or "auth_basic_user_file" not in line:
            continue
        auth_file = line.split("auth_basic_user_file", 1)[1].split(";", 1)[0].strip().strip('"').strip("'")
        break
    if not auth_file:
        raise RuntimeError("public_basic_auth_user_file_not_configured")
    auth_path = Path(auth_file)
    if not auth_path.is_absolute():
        auth_path = Path("/etc/nginx") / auth_path
    try:
        content = auth_path.read_text(encoding="utf-8")
    except PermissionError:
        read_result = proc(["sudo", "-n", "cat", str(auth_path)], timeout=30)
        if read_result.returncode != 0:
            raise RuntimeError("public_basic_auth_user_file_unreadable")
        content = read_result.stdout
    for raw in content.splitlines():
        line = raw.strip()
        if line and ":" in line:
            username = line.split(":", 1)[0].strip()
            if username:
                return username
    raise RuntimeError("public_basic_auth_username_missing")


def public_request(
'''

OLD_USERNAME_PROMPT = '''        username = input("Public Basic Auth username: ").strip()
        password = getpass.getpass("Public Basic Auth password: ")
        if not username or not password:
            raise RuntimeError("public_basic_auth_missing")
'''

NEW_USERNAME_PROMPT = '''        username = basic_auth_username()
        log(f"PUBLIC_BASIC_AUTH_USERNAME={username}")
        password = getpass.getpass("Public Basic Auth password: ")
        if not password:
            raise RuntimeError("public_basic_auth_password_missing")
'''


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if new in text:
        return text, False
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1), True


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    text, changed_function = replace_once(text, OLD_FUNCTION, NEW_FUNCTION, "evidence_ready")
    text, changed_extraction = replace_once(text, OLD_EXTRACTION, NEW_EXTRACTION, "index_extraction")
    text, changed_username_function = replace_once(text, OLD_USERNAME_ANCHOR, NEW_USERNAME_ANCHOR, "basic_auth_username")
    text, changed_username_prompt = replace_once(text, OLD_USERNAME_PROMPT, NEW_USERNAME_PROMPT, "basic_auth_prompt")
    if changed_function or changed_extraction or changed_username_function or changed_username_prompt:
        PATH.write_text(text, encoding="utf-8")
        print("PUBLIC_READONLY_E2E_RUNNER_PATCHED=yes")
    else:
        print("PUBLIC_READONLY_E2E_RUNNER_PATCHED=already")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
