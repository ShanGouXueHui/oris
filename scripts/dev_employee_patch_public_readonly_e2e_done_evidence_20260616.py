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
    if changed_function or changed_extraction:
        PATH.write_text(text, encoding="utf-8")
        print("PUBLIC_READONLY_E2E_RUNNER_PATCHED=yes")
    else:
        print("PUBLIC_READONLY_E2E_RUNNER_PATCHED=already")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
