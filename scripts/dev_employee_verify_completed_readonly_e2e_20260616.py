#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS = Path("/home/admin/projects/oris")
PRODUCT = Path("/home/admin/projects/oris-final-acceptance-api")
INTAKE = "http://127.0.0.1:18892"
SERVICES = {
    "WEB_CONSOLE_SERVICE": "oris-dev-employee-web-console.service",
    "INTAKE_SERVICE": "oris-dev-employee-intake.service",
    "BRIDGE_SERVICE": "oris-dev-employee-bridge.service",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(args: list[str], cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def output(args: list[str], cwd: Path, timeout: int = 120) -> str:
    result = run(args, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[-1200:]
        raise RuntimeError(f"command_failed:{args[0]}:{tail}")
    return result.stdout.strip()


def service_state(name: str) -> str:
    result = run(["systemctl", "--user", "is-active", name], timeout=30)
    return (result.stdout or result.stderr or "unknown").strip()


def status_payload(task_id: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{INTAKE}/goals/{task_id}", timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
        if response.status != 200 or not isinstance(payload, dict):
            raise RuntimeError(f"status_api_invalid:{response.status}")
        return payload


def done_record(payload: dict[str, Any]) -> dict[str, Any]:
    queue = payload.get("queue") if isinstance(payload.get("queue"), list) else []
    for item in queue:
        if not isinstance(item, dict) or item.get("suffix") != "done":
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        index_result = data.get("oris_evidence_index_result") if isinstance(data.get("oris_evidence_index_result"), dict) else {}
        if data.get("status") == "completed" and index_result.get("commit_sha"):
            return data
    return {}


def write_process(path: Path, result: subprocess.CompletedProcess[str]) -> None:
    path.write_text(
        f"return_code={result.returncode}\n\n===== stdout =====\n{result.stdout or ''}\n===== stderr =====\n{result.stderr or ''}\n",
        encoding="utf-8",
    )


def commit_logs(paths: list[Path], message: str) -> str:
    rel = [path.resolve().relative_to(ORIS.resolve()).as_posix() for path in paths if path.is_file()]
    add = run(["git", "add", "--", *rel], cwd=ORIS, timeout=120)
    if add.returncode != 0:
        return "LOG_ADD_FAILED"
    changed = run(["git", "diff", "--cached", "--quiet", "--", *rel], cwd=ORIS, timeout=60)
    if changed.returncode == 0:
        return "NO_LOG_CHANGES"
    if changed.returncode != 1:
        return "LOG_DIFF_FAILED"
    commit = run(["git", "commit", "--only", "-m", message, "--", *rel], cwd=ORIS, timeout=180)
    if commit.returncode != 0:
        return "LOG_COMMIT_FAILED"
    push = run(["git", "push", "origin", "main"], cwd=ORIS, timeout=180)
    if push.returncode != 0:
        return "LOG_PUSH_FAILED"
    return output(["git", "rev-parse", "HEAD"], ORIS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    args = parser.parse_args()
    task_id = args.task_id

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_dir = ORIS / "logs/dev_employee/web_console_public_submit_e2e"
    log_dir.mkdir(parents=True, exist_ok=True)
    main_log = log_dir / f"{task_id}.verify-completed-{stamp}.log"
    status_log = log_dir / f"{task_id}.verify-status-{stamp}.json"
    compile_log = log_dir / f"{task_id}.verify-pycompile-{stamp}.txt"
    pytest_log = log_dir / f"{task_id}.verify-pytest-{stamp}.txt"
    endpoint_log = log_dir / f"{task_id}.verify-endpoint-{stamp}.txt"
    verification_log = log_dir / f"{task_id}.verification-{stamp}.json"

    state: dict[str, Any] = {
        "RESULT": "FAILED",
        "TASK_ID": task_id,
        "FINAL_STATUS": "unknown",
        "CANONICAL_STATUS": "unknown",
        "TERMINAL": "false",
        "FAILURE_CODE": "",
        "PRODUCT_PY_COMPILE": "NOT_RUN",
        "PRODUCT_PYTEST": "NOT_RUN",
        "ENDPOINT_CONTRACT": "NOT_RUN",
        "HOST_PYTEST_EVIDENCE": "NOT_VERIFIED",
        "STRICT_RESULT_SCHEMA": "NOT_VERIFIED",
        "PRODUCT_COMMIT_SHA": "",
        "PRODUCT_REMOTE_SHA": "",
        "PRODUCT_LOCAL_HEAD": "",
        "PRODUCT_REMOTE_MAIN": "",
        "PRODUCT_SHA_MATCH": "NO",
        "PRODUCT_WORKTREE_CLEAN": "NO",
        "ORIS_EVIDENCE_COMMIT_SHA": "",
        "ORIS_EVIDENCE_REMOTE_SHA": "",
        "ORIS_EVIDENCE_INDEX_COMMIT_SHA": "",
        "ORIS_EVIDENCE_ON_REMOTE": "NO",
        "ORIS_INDEX_ON_REMOTE": "NO",
        "LOG_COMMIT": "",
        "REAL_PRODUCT_TASK_SUBMITTED": "YES",
        "NEW_PRODUCT_TASK_SUBMITTED": "NO",
        "NEXT_ACTION": "INSPECT_GITHUB_EVIDENCE",
    }
    lines: list[str] = []

    def log(text: str) -> None:
        lines.append(text)
        print(text, flush=True)

    try:
        if os.geteuid() == 0 or os.environ.get("USER") != "admin":
            raise RuntimeError("wrong_linux_user")
        for key, service in SERVICES.items():
            state[key] = service_state(service)
            if state[key] != "active":
                raise RuntimeError(f"service_not_active:{service}")

        payload = status_payload(task_id)
        status_log.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        state["FINAL_STATUS"] = str(payload.get("status") or "unknown")
        state["CANONICAL_STATUS"] = str(payload.get("canonical_status") or state["FINAL_STATUS"])
        state["TERMINAL"] = "true" if payload.get("terminal") is True else "false"
        state["FAILURE_CODE"] = str(payload.get("failure_code") or "")
        if state["CANONICAL_STATUS"] != "completed" or state["TERMINAL"] != "true":
            raise RuntimeError("task_not_completed")

        done = done_record(payload)
        if not done:
            raise RuntimeError("done_record_missing")
        index_result = done.get("oris_evidence_index_result") or {}
        evidence = payload.get("github_evidence") or {}
        labels = {str(item.get("label")) for item in evidence.get("files", []) if isinstance(item, dict)}

        state["PRODUCT_COMMIT_SHA"] = str(evidence.get("product_commit_sha") or "")
        state["PRODUCT_REMOTE_SHA"] = str(evidence.get("product_remote_sha") or "")
        state["ORIS_EVIDENCE_COMMIT_SHA"] = str(evidence.get("oris_evidence_commit_sha") or "")
        state["ORIS_EVIDENCE_REMOTE_SHA"] = str(evidence.get("oris_evidence_remote_sha") or "")
        state["ORIS_EVIDENCE_INDEX_COMMIT_SHA"] = str(index_result.get("commit_sha") or "")
        state["HOST_PYTEST_EVIDENCE"] = "PASS" if "host_pytest_log" in labels else "FAILED"
        state["STRICT_RESULT_SCHEMA"] = "PASS" if evidence.get("strict_result_schema") is True else "FAILED"

        python_bin = PRODUCT / ".venv/bin/python"
        compile_result = run([str(python_bin), "-m", "py_compile", "app/main.py"], cwd=PRODUCT, timeout=120)
        write_process(compile_log, compile_result)
        state["PRODUCT_PY_COMPILE"] = "PASS" if compile_result.returncode == 0 else "FAILED"
        if compile_result.returncode != 0:
            raise RuntimeError("product_py_compile_failed")

        pytest_result = run([str(python_bin), "-m", "pytest", "-q"], cwd=PRODUCT, timeout=600)
        write_process(pytest_log, pytest_result)
        state["PRODUCT_PYTEST"] = "PASS" if pytest_result.returncode == 0 else "FAILED"
        if pytest_result.returncode != 0:
            raise RuntimeError("product_pytest_failed")

        snippet = (
            "import json\n"
            "from fastapi.testclient import TestClient\n"
            "from app.main import app\n"
            "r=TestClient(app).get('/readonly-e2e')\n"
            "b=r.json()\n"
            "print(json.dumps({'status_code':r.status_code,'body':b},sort_keys=True))\n"
            "raise SystemExit(0 if r.status_code==200 and b=={'readonly_e2e':True} else 1)\n"
        )
        endpoint_result = run([str(python_bin), "-c", snippet], cwd=PRODUCT, timeout=120)
        write_process(endpoint_log, endpoint_result)
        state["ENDPOINT_CONTRACT"] = "PASS" if endpoint_result.returncode == 0 else "FAILED"
        if endpoint_result.returncode != 0:
            raise RuntimeError("endpoint_contract_failed")

        state["PRODUCT_LOCAL_HEAD"] = output(["git", "rev-parse", "HEAD"], PRODUCT)
        remote_line = output(["git", "ls-remote", "origin", "refs/heads/main"], PRODUCT)
        state["PRODUCT_REMOTE_MAIN"] = remote_line.split()[0] if remote_line else ""
        dirty = output(["git", "status", "--porcelain", "--untracked-files=no"], PRODUCT)
        state["PRODUCT_WORKTREE_CLEAN"] = "YES" if not dirty else "NO"

        shas = [
            state["PRODUCT_COMMIT_SHA"],
            state["PRODUCT_REMOTE_SHA"],
            state["PRODUCT_LOCAL_HEAD"],
            state["PRODUCT_REMOTE_MAIN"],
        ]
        state["PRODUCT_SHA_MATCH"] = "YES" if all(shas) and len(set(shas)) == 1 else "NO"

        for key, expected in [
            ("PRODUCT_SHA_MATCH", "YES"),
            ("PRODUCT_WORKTREE_CLEAN", "YES"),
            ("HOST_PYTEST_EVIDENCE", "PASS"),
            ("STRICT_RESULT_SCHEMA", "PASS"),
        ]:
            if state[key] != expected:
                raise RuntimeError(f"verification_failed:{key}:{state[key]}")

        if state["ORIS_EVIDENCE_COMMIT_SHA"] != state["ORIS_EVIDENCE_REMOTE_SHA"]:
            raise RuntimeError("oris_evidence_sha_mismatch")
        fetch = run(["git", "fetch", "origin", "main"], cwd=ORIS, timeout=180)
        if fetch.returncode != 0:
            raise RuntimeError("oris_fetch_failed")
        ev = run(["git", "merge-base", "--is-ancestor", state["ORIS_EVIDENCE_COMMIT_SHA"], "origin/main"], cwd=ORIS)
        idx = run(["git", "merge-base", "--is-ancestor", state["ORIS_EVIDENCE_INDEX_COMMIT_SHA"], "origin/main"], cwd=ORIS)
        state["ORIS_EVIDENCE_ON_REMOTE"] = "YES" if ev.returncode == 0 else "NO"
        state["ORIS_INDEX_ON_REMOTE"] = "YES" if idx.returncode == 0 else "NO"
        if state["ORIS_EVIDENCE_ON_REMOTE"] != "YES" or state["ORIS_INDEX_ON_REMOTE"] != "YES":
            raise RuntimeError("oris_evidence_not_on_remote")

        state["RESULT"] = "PASS"
        state["NEXT_ACTION"] = "FINAL_ACCEPTANCE_COMPLETE"
    except Exception as exc:
        if not state["FAILURE_CODE"]:
            state["FAILURE_CODE"] = str(exc).splitlines()[0][:400]
        state["RESULT"] = "FAILED"
    finally:
        for key, service in SERVICES.items():
            state[key] = service_state(service)
        state["CHECKED_AT"] = now_iso()
        verification_log.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for key in [
            "RESULT", "TASK_ID", "FINAL_STATUS", "CANONICAL_STATUS", "TERMINAL", "FAILURE_CODE",
            "PRODUCT_PY_COMPILE", "PRODUCT_PYTEST", "ENDPOINT_CONTRACT", "HOST_PYTEST_EVIDENCE",
            "STRICT_RESULT_SCHEMA", "PRODUCT_COMMIT_SHA", "PRODUCT_REMOTE_SHA", "PRODUCT_LOCAL_HEAD",
            "PRODUCT_REMOTE_MAIN", "PRODUCT_SHA_MATCH", "PRODUCT_WORKTREE_CLEAN",
            "ORIS_EVIDENCE_COMMIT_SHA", "ORIS_EVIDENCE_REMOTE_SHA", "ORIS_EVIDENCE_INDEX_COMMIT_SHA",
            "ORIS_EVIDENCE_ON_REMOTE", "ORIS_INDEX_ON_REMOTE",
        ]:
            log(f"{key}={state[key]}")
        main_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        state["LOG_COMMIT"] = commit_logs(
            [main_log, status_log, compile_log, pytest_log, endpoint_log, verification_log],
            f"test(dev-employee): verify completed readonly E2E {task_id}",
        )
        if state["LOG_COMMIT"] in {"LOG_ADD_FAILED", "LOG_DIFF_FAILED", "LOG_COMMIT_FAILED", "LOG_PUSH_FAILED"}:
            state["RESULT"] = "FAILED"
            state["FAILURE_CODE"] = state["FAILURE_CODE"] or state["LOG_COMMIT"].lower()
            state["NEXT_ACTION"] = "RESOLVE_ORIS_EVIDENCE_PUSH"

        print("\n===== SUMMARY =====")
        for key in [
            "RESULT", "TASK_ID", "FINAL_STATUS", "CANONICAL_STATUS", "TERMINAL", "FAILURE_CODE",
            "PRODUCT_PY_COMPILE", "PRODUCT_PYTEST", "ENDPOINT_CONTRACT", "HOST_PYTEST_EVIDENCE",
            "STRICT_RESULT_SCHEMA", "PRODUCT_COMMIT_SHA", "PRODUCT_REMOTE_SHA", "PRODUCT_LOCAL_HEAD",
            "PRODUCT_REMOTE_MAIN", "PRODUCT_SHA_MATCH", "PRODUCT_WORKTREE_CLEAN",
            "ORIS_EVIDENCE_COMMIT_SHA", "ORIS_EVIDENCE_REMOTE_SHA", "ORIS_EVIDENCE_INDEX_COMMIT_SHA",
            "ORIS_EVIDENCE_ON_REMOTE", "ORIS_INDEX_ON_REMOTE", "LOG_COMMIT",
            "WEB_CONSOLE_SERVICE", "INTAKE_SERVICE", "BRIDGE_SERVICE",
            "REAL_PRODUCT_TASK_SUBMITTED", "NEW_PRODUCT_TASK_SUBMITTED", "NEXT_ACTION",
        ]:
            print(f"{key}={state[key]}")
        print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
        print("===== END SUMMARY =====")

    return 0 if state["RESULT"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
