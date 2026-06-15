#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path("/home/admin/projects/oris")


def replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def patch_bridge() -> bool:
    path = ROOT / "scripts/dev_employee_supervised_bridge_v2.py"
    changed = False
    changed |= replace_once(
        path,
        "from dev_employee_result_validator import validate_result\n",
        """from dev_employee_codex_auth_preflight import classify_codex_failure, run_codex_auth_preflight
from dev_employee_result_validator import validate_result
from dev_employee_task_states import classify as classify_task_state
""",
    )
    changed |= replace_once(
        path,
        """def next_recommended_action(status: str) -> str:
    if status in {"blocked_result_schema_invalid", "blocked_skill_resolution_invalid"}:
        return "Inspect GitHub failure evidence and Codex log; update autonomous prompt, resolver, or bridge enforcement, then rerun with a new task id."
    if status == "blocked_host_checks_failed":
        return "Inspect host check logs from GitHub evidence; fix product implementation or tests, then rerun with a new task id."
    if status == "codex_failed":
        return "Inspect Codex log and runtime descriptor; repair prompt/tooling or resource issue, then rerun with a new task id."
    if status in {"blocked_product_push_failed", "blocked_oris_push_failed"}:
        return "Inspect Git push evidence and repository state; resolve Git synchronization or permissions issue, then rerun or resume safely."
    return "Inspect failure details and available logs; apply the smallest safe platform or product fix, then rerun with a new task id."
""",
        """def next_recommended_action(status: str, failure_code: str | None = None) -> str:
    if failure_code == "codex_authentication":
        return "Reauthenticate Codex as Linux user admin, verify non-interactive and bridge-context preflight, then rerun with a new task id."
    if status in {"blocked_result_schema_invalid", "blocked_skill_resolution_invalid"}:
        return "Inspect GitHub failure evidence and Codex log; update autonomous prompt, resolver, or bridge enforcement, then rerun with a new task id."
    if status in {"blocked_host_checks_failed", "local_checks_failed"}:
        return "Inspect host check logs from GitHub evidence; fix product implementation or tests, then rerun with a new task id."
    if status in {"codex_failed", "failed", "preflight_failed"}:
        return "Inspect executor preflight and Codex logs; repair authentication, tooling, or resource issue, then rerun with a new task id."
    if status in {"blocked_product_push_failed", "blocked_oris_push_failed", "remote_verification_failed"}:
        return "Inspect Git push evidence and repository state; resolve Git synchronization or permissions issue, then rerun or resume safely."
    return "Inspect failure details and available logs; apply the smallest safe platform or product fix, then rerun with a new task id."
""",
    )
    changed |= replace_once(
        path,
        """    evidence = {
        "task_id": task_id,
        "status": status,
        "updated_at": now_iso(),
""",
        """    state = classify_task_state(status, extra or {})
    failure_code = state.get("failure_code")
    evidence = {
        "task_id": task_id,
        "status": status,
        "canonical_status": state["canonical_status"],
        "terminal": state["terminal"],
        "failure_code": failure_code,
        "updated_at": now_iso(),
""",
    )
    changed |= replace_once(
        path,
        """        "next_recommended_action": next_recommended_action(status),
""",
        """        "next_recommended_action": next_recommended_action(status, failure_code),
""",
    )
    changed |= replace_once(
        path,
        """        for optional_key in ["checks", "product_result", "oris_result", "codex_result", "schema_errors", "skill_resolution_errors", "return_code", "last_error"]:
""",
        """        for optional_key in ["checks", "product_result", "oris_result", "codex_result", "schema_errors", "skill_resolution_errors", "return_code", "last_error", "failure_code", "legacy_status", "executor_preflight", "codex_auth_preflight_log_path"]:
""",
    )
    changed |= replace_once(
        path,
        """    latest = {
        "task_id": task_id,
        "status": status,
        "oris_evidence_pending": False,
""",
        """    latest = {
        "task_id": task_id,
        "status": status,
        "canonical_status": state["canonical_status"],
        "terminal": state["terminal"],
        "failure_code": failure_code,
        "oris_evidence_pending": False,
""",
    )
    changed |= replace_once(
        path,
        """        task.update({"status": "codex_running", "codex_log_path": str(codex_log), "codex_result_path": str(result_path), "started_at": now_iso()})
        write_json(RUN_DIR / f"{task_id}.json", task)
        rc = invoke_codex(task, codex_log, result_path)
        if rc != 0:
            return fail_task(task_path, task, "codex_failed", {"return_code": rc})
""",
        """        codex_bin = safe_path(task.get("codex_bin") or str(DEFAULT_CODEX), [Path("/home/admin")])
        workdir = safe_path(task.get("workdir", str(PROJECTS_DIR)), [PROJECTS_DIR])
        preflight_log = LOG_DIR / f"{task_id}.codex_auth_preflight.json"
        task.update({
            "status": "preflight",
            "codex_log_path": str(codex_log),
            "codex_result_path": str(result_path),
            "codex_auth_preflight_log_path": str(preflight_log),
            "started_at": now_iso(),
        })
        write_json(RUN_DIR / f"{task_id}.json", task)
        executor_preflight = run_codex_auth_preflight(
            codex_bin,
            workdir,
            log_path=preflight_log,
        )
        if not executor_preflight.get("ok"):
            return fail_task(
                task_path,
                task,
                "preflight_failed",
                {
                    "failure_code": executor_preflight.get("failure_code") or "codex_preflight_failed",
                    "executor_preflight": executor_preflight,
                    "codex_auth_preflight_log_path": str(preflight_log),
                },
            )
        task["status"] = "codex_running"
        task["executor_preflight"] = {
            key: executor_preflight.get(key)
            for key in ["ok", "status", "executor_path", "executor_version", "linux_user", "uid", "home", "workdir"]
        }
        write_json(RUN_DIR / f"{task_id}.json", task)
        rc = invoke_codex(task, codex_log, result_path)
        if rc != 0:
            codex_output = codex_log.read_text(encoding="utf-8", errors="replace") if codex_log.exists() else ""
            failure_code = classify_codex_failure(codex_output, rc)
            return fail_task(
                task_path,
                task,
                "failed",
                {
                    "return_code": rc,
                    "failure_code": failure_code,
                    "legacy_status": "codex_failed",
                },
            )
""",
    )
    return changed


def patch_intake() -> bool:
    path = ROOT / "scripts/dev_employee_intake_api.py"
    changed = False
    changed |= replace_once(
        path,
        "from urllib.parse import unquote, urlparse\n",
        """from urllib.parse import unquote, urlparse

from dev_employee_task_states import classify as classify_task_state
""",
    )
    changed |= replace_once(
        path,
        """    latest = None
    latest_path = LOG_DIR / "latest_task_progress.json"
""",
        """    state = classify_task_state(status, primary_run or {})
    latest = None
    latest_path = LOG_DIR / "latest_task_progress.json"
""",
    )
    changed |= replace_once(
        path,
        """        "task_id": task_id,
        "status": status,
        "catalog": catalog,
""",
        """        "task_id": task_id,
        "status": status,
        "canonical_status": state["canonical_status"],
        "terminal": state["terminal"],
        "failure_code": state["failure_code"],
        "catalog": catalog,
""",
    )
    changed |= replace_once(
        path,
        """        data = read_json(path)
        items.append({"task_id": data.get("task_id"), "project_key": data.get("project_key"), "status": data.get("status"), "created_at": data.get("created_at"), "path": str(path)})
""",
        """        data = read_json(path)
        task_id = str(data.get("task_id") or "")
        current = task_status(task_id) if task_id else {}
        items.append({
            "task_id": task_id or None,
            "project_key": data.get("project_key"),
            "status": current.get("status") or data.get("status"),
            "canonical_status": current.get("canonical_status"),
            "terminal": current.get("terminal"),
            "failure_code": current.get("failure_code"),
            "created_at": data.get("created_at"),
            "path": str(path),
        })
""",
    )
    return changed


def patch_finisher() -> bool:
    path = ROOT / "scripts/dev_employee_finish_public_web_submit_e2e.sh"
    changed = False
    changed |= replace_once(
        path,
        """read -p "Task ID submitted from public Web UI: " TASK_ID
""",
        """TASK_ID="${1:-}"
if [ -z "$TASK_ID" ]; then
  read -p "Task ID submitted from public Web UI: " TASK_ID
fi
""",
    )
    changed |= replace_once(
        path,
        """FINAL_STATUS="unknown"
PRODUCT_COMMIT=""
""",
        """FINAL_STATUS="unknown"
CANONICAL_STATUS="unknown"
TERMINAL="false"
FAILURE_CODE=""
PRODUCT_COMMIT=""
""",
    )
    changed |= replace_once(
        path,
        """    echo "POLL=$i HTTP=$HTTP_CODE STATUS=$FINAL_STATUS"
    if [ "$FINAL_STATUS" = "completed" ] || [ "$FINAL_STATUS" = "failed" ] || [ "$FINAL_STATUS" = "error" ]; then
      break
    fi
""",
        """    CANONICAL_STATUS="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print(data.get('canonical_status') or data.get('status') or 'unknown')
except Exception:
    print('unknown')
PY
)"
    TERMINAL="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print('true' if data.get('terminal') is True else 'false')
except Exception:
    print('false')
PY
)"
    FAILURE_CODE="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    print(data.get('failure_code') or '')
except Exception:
    print('')
PY
)"
    if [ "$TERMINAL" != "true" ]; then
      TERMINAL="$(python3 scripts/dev_employee_task_states.py "$FINAL_STATUS" --field terminal 2>/dev/null || echo false)"
      CANONICAL_STATUS="$(python3 scripts/dev_employee_task_states.py "$FINAL_STATUS" --field canonical_status 2>/dev/null || echo "$FINAL_STATUS")"
    fi
    echo "POLL=$i HTTP=$HTTP_CODE STATUS=$FINAL_STATUS CANONICAL=$CANONICAL_STATUS TERMINAL=$TERMINAL"
    if [ "$TERMINAL" = "true" ]; then
      break
    fi
""",
    )
    changed |= replace_once(
        path,
        """echo "RESULT=$([ "$FINAL_STATUS" = "completed" ] && echo PASS || echo REVIEW)"
echo "TASK_ID=$TASK_ID"
echo "FINAL_STATUS=$FINAL_STATUS"
""",
        """if [ "$CANONICAL_STATUS" = "completed" ]; then
  SUMMARY_RESULT="PASS"
elif [ "$TERMINAL" = "true" ]; then
  SUMMARY_RESULT="FAILED"
else
  SUMMARY_RESULT="REVIEW"
fi
echo "RESULT=$SUMMARY_RESULT"
echo "TASK_ID=$TASK_ID"
echo "FINAL_STATUS=$FINAL_STATUS"
echo "CANONICAL_STATUS=$CANONICAL_STATUS"
echo "TERMINAL=$TERMINAL"
echo "FAILURE_CODE=$FAILURE_CODE"
""",
    )
    return changed


def main() -> int:
    results = {
        "bridge": patch_bridge(),
        "intake": patch_intake(),
        "finisher": patch_finisher(),
    }
    for name, changed in results.items():
        print(f"{name.upper()}_PATCHED={'yes' if changed else 'already'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
