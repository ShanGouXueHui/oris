#!/usr/bin/env python3
"""Final public Web acceptance runner for the ORIS Codex-backed Dev Employee.

The runner submits one new task through https://control.orisfy.com, waits for a
terminal state and complete GitHub evidence, independently reruns product tests,
and commits sanitized verification logs to ORIS main.
"""

from __future__ import annotations

import base64
import getpass
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS = Path("/home/admin/projects/oris")
PRODUCT = Path("/home/admin/projects/oris-final-acceptance-api")
ENV_FILE = Path.home() / ".config/oris/dev_employee_enqueue.env"
PUBLIC = "https://control.orisfy.com"
PROJECT = "oris-final-acceptance-api"
PRODUCT_REPO = "ShanGouXueHui/oris-final-acceptance-api"
HARDENING_COMMIT = "57cf6eccb1bbf7cc4e6ddd79eab94e7530d3fe5c"
SERVICES = {
    "WEB_CONSOLE_SERVICE": "oris-dev-employee-web-console.service",
    "INTAKE_SERVICE": "oris-dev-employee-intake.service",
    "BRIDGE_SERVICE": "oris-dev-employee-bridge.service",
}


def timestamp(fmt: str = "%Y%m%d-%H%M%S") -> str:
    return datetime.now(timezone.utc).astimezone().strftime(fmt)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def proc(args: list[str], cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def command_output(args: list[str], cwd: Path, timeout: int = 120) -> str:
    result = proc(args, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[-1500:]
        raise RuntimeError(f"command_failed:{args[0]}:{tail}")
    return result.stdout.strip()


def service_state(name: str) -> str:
    result = proc(["systemctl", "--user", "is-active", name], timeout=30)
    return (result.stdout or result.stderr or "unknown").strip()


def env_value(key: str) -> str:
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
    method: str,
    path: str,
    *,
    username: str = "",
    password: str = "",
    console_token: str = "",
    body: dict[str, Any] | None = None,
    timeout: int = 45,
) -> tuple[int, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if username and password:
        encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {encoded}"
    if console_token:
        headers["X-ORIS-Console-Token"] = console_token
    request = urllib.request.Request(PUBLIC + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(text) if text else {}
            except json.JSONDecodeError:
                payload = {"raw": text[:4000]}
            return response.status, payload
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = {"raw": text[:4000]}
        return exc.code, payload
    except urllib.error.URLError as exc:
        return 599, {"error": "url_error", "message": str(exc.reason)}


def endpoint_probe(path: Path) -> dict[str, Any]:
    python_bin = PRODUCT / ".venv/bin/python"
    snippet = r'''
import json
from fastapi.testclient import TestClient
from app.main import app
response = TestClient(app).get("/readonly-e2e")
try:
    body = response.json()
except Exception:
    body = response.text
print(json.dumps({
    "status_code": response.status_code,
    "body": body,
    "exact": response.status_code == 200 and body == {"readonly_e2e": True},
}, ensure_ascii=False, sort_keys=True))
'''
    result = proc([str(python_bin), "-c", snippet], cwd=PRODUCT, timeout=120)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((result.stdout or "") + (result.stderr or ""), encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"endpoint_probe_failed:{(result.stderr or result.stdout)[-1500:]}")
    try:
        return json.loads((result.stdout or "").strip().splitlines()[-1])
    except Exception as exc:
        raise RuntimeError(f"endpoint_probe_json_invalid:{type(exc).__name__}") from exc


def save_process(path: Path, result: subprocess.CompletedProcess[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"return_code={result.returncode}\n\n===== stdout =====\n{result.stdout or ''}\n===== stderr =====\n{result.stderr or ''}\n",
        encoding="utf-8",
    )


def completed_done_record(payload: dict[str, Any]) -> dict[str, Any]:
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


def git_commit_logs(paths: list[Path], message: str) -> str:
    relative = [path.resolve().relative_to(ORIS.resolve()).as_posix() for path in paths if path.is_file()]
    if not relative:
        return "NO_LOG_FILES"
    add = proc(["git", "add", "--", *relative], cwd=ORIS, timeout=120)
    if add.returncode != 0:
        return "LOG_ADD_FAILED"
    changed = proc(["git", "diff", "--cached", "--quiet", "--", *relative], cwd=ORIS, timeout=60)
    if changed.returncode == 0:
        return "NO_LOG_CHANGES"
    if changed.returncode != 1:
        return "LOG_DIFF_FAILED"
    commit = proc(["git", "commit", "--only", "-m", message, "--", *relative], cwd=ORIS, timeout=180)
    if commit.returncode != 0:
        return "LOG_COMMIT_FAILED"
    push = proc(["git", "push", "origin", "main"], cwd=ORIS, timeout=180)
    if push.returncode != 0:
        return "LOG_PUSH_FAILED"
    return command_output(["git", "rev-parse", "HEAD"], ORIS)


def main() -> int:
    task_id = f"goal-{PROJECT}-readonly-e2e-{timestamp()}"
    log_dir = ORIS / "logs/dev_employee/web_console_public_submit_e2e"
    log_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "main": log_dir / f"{task_id}.final-acceptance.log",
        "submit": log_dir / f"{task_id}.submit.json",
        "status": log_dir / f"{task_id}.status.json",
        "verification": log_dir / f"{task_id}.verification.json",
        "py_compile": log_dir / f"{task_id}.product-py-compile.txt",
        "pytest": log_dir / f"{task_id}.product-pytest.txt",
        "endpoint": log_dir / f"{task_id}.endpoint-contract.txt",
    }
    state: dict[str, Any] = {
        "RESULT": "FAILED",
        "TASK_ID": task_id,
        "PUBLIC_SUBMIT_HTTP": "",
        "FINAL_STATUS": "unknown",
        "CANONICAL_STATUS": "unknown",
        "TERMINAL": "false",
        "FAILURE_CODE": "",
        "PRODUCT_PY_COMPILE": "NOT_RUN",
        "PRODUCT_PYTEST": "NOT_RUN",
        "ENDPOINT_CONTRACT": "NOT_RUN",
        "HOST_PYTEST_EVIDENCE": "NOT_VERIFIED",
        "STRICT_RESULT_SCHEMA": "NOT_VERIFIED",
        "BASELINE_PRODUCT_SHA": "",
        "PRODUCT_COMMIT_SHA": "",
        "PRODUCT_REMOTE_SHA": "",
        "PRODUCT_LOCAL_HEAD": "",
        "PRODUCT_REMOTE_MAIN": "",
        "PRODUCT_SHA_MATCH": "NO",
        "PRODUCT_CHANGED": "NO",
        "PRODUCT_WORKTREE_CLEAN": "NO",
        "ORIS_EVIDENCE_COMMIT_SHA": "",
        "ORIS_EVIDENCE_REMOTE_SHA": "",
        "ORIS_EVIDENCE_INDEX_COMMIT_SHA": "",
        "ORIS_EVIDENCE_ON_REMOTE": "NO",
        "ORIS_INDEX_ON_REMOTE": "NO",
        "LOG_COMMIT": "",
        "REAL_PRODUCT_TASK_SUBMITTED": "NO",
        "NEXT_ACTION": "INSPECT_GITHUB_EVIDENCE",
    }
    lines: list[str] = []
    status_payload: dict[str, Any] = {}
    username = ""
    password = ""
    console_token = ""

    def log(text: str = "") -> None:
        lines.append(text)
        print(text, flush=True)

    try:
        if os.geteuid() == 0 or getpass.getuser() != "admin":
            raise RuntimeError("wrong_linux_user")
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise RuntimeError("interactive_tty_required")
        if not ORIS.is_dir() or not PRODUCT.is_dir():
            raise RuntimeError("required_repository_missing")

        log("===== timestamp =====")
        log(now_iso())
        log("===== task =====")
        log(f"TASK_ID={task_id}")
        log(f"PUBLIC_ENTRY={PUBLIC}")
        for output_name, service in SERVICES.items():
            current = service_state(service)
            log(f"{output_name}={current}")
            if current != "active":
                raise RuntimeError(f"service_not_active:{service}")

        if proc(["git", "merge-base", "--is-ancestor", HARDENING_COMMIT, "HEAD"], cwd=ORIS).returncode != 0:
            raise RuntimeError("hardening_commit_not_present")
        if not (PRODUCT / ".venv/bin/python").is_file():
            raise RuntimeError("product_venv_missing")
        if command_output(["git", "status", "--porcelain", "--untracked-files=no"], PRODUCT):
            raise RuntimeError("product_tracked_worktree_dirty")

        baseline = command_output(["git", "rev-parse", "HEAD"], PRODUCT)
        remote_line = command_output(["git", "ls-remote", "origin", "refs/heads/main"], PRODUCT)
        baseline_remote = remote_line.split()[0] if remote_line else ""
        state["BASELINE_PRODUCT_SHA"] = baseline
        log(f"BASELINE_PRODUCT_SHA={baseline}")
        log(f"BASELINE_PRODUCT_REMOTE_SHA={baseline_remote}")
        if not baseline_remote or baseline != baseline_remote:
            raise RuntimeError("product_baseline_remote_sha_mismatch")

        before = endpoint_probe(paths["endpoint"])
        log(f"BASELINE_ENDPOINT_STATUS={before.get('status_code')}")
        log(f"BASELINE_ENDPOINT_EXACT={'yes' if before.get('exact') else 'no'}")
        if before.get("status_code") != 404:
            raise RuntimeError("readonly_e2e_baseline_not_404")

        console_token = env_value("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN")
        if not console_token:
            raise RuntimeError("console_token_missing")
        username = input("Public Basic Auth username: ").strip()
        password = getpass.getpass("Public Basic Auth password: ")
        if not username or not password:
            raise RuntimeError("public_basic_auth_missing")

        unauth_code, _ = public_request("GET", "/health")
        log(f"PUBLIC_UNAUTH_HEALTH_HTTP={unauth_code}")
        if unauth_code != 401:
            raise RuntimeError("public_basic_auth_boundary_not_enforced")
        health_code, health = public_request("GET", "/health", username=username, password=password)
        log(f"PUBLIC_AUTH_HEALTH_HTTP={health_code}")
        if health_code != 200 or not isinstance(health, dict) or health.get("status") != "ok":
            raise RuntimeError("public_authenticated_health_failed")
        projects_code, projects_payload = public_request(
            "GET",
            "/api/projects",
            username=username,
            password=password,
            console_token=console_token,
        )
        projects = projects_payload.get("projects") if isinstance(projects_payload, dict) else []
        log(f"PUBLIC_PROJECTS_HTTP={projects_code}")
        log(f"PROJECT_ALLOWED={'yes' if PROJECT in projects else 'no'}")
        if projects_code != 200 or PROJECT not in projects:
            raise RuntimeError("public_project_allowlist_validation_failed")

        payload = {
            "task_id": task_id,
            "project_key": PROJECT,
            "objective": (
                'Add a minimal FastAPI GET /readonly-e2e endpoint that returns exactly {"readonly_e2e": true}. '
                "Add pytest coverage for the status code and exact JSON response. Run the complete existing test "
                "suite, commit the product changes to main, push them to the configured GitHub remote, and emit "
                "strict structured evidence with product and remote commit SHAs."
            ),
            "constraints": [
                "Modify only the standalone product repository; do not place product code in ORIS.",
                "Preserve all existing task-board API behavior and public contracts.",
                "Use existing FastAPI and pytest conventions.",
                "Keep implementation minimal and deterministic.",
                "Do not add external dependencies unless strictly necessary.",
                "Do not ask the human to decide routine engineering details.",
                "Commit and push only after all tests pass.",
            ],
            "expected_checks": [
                "python3 -m py_compile app/main.py",
                "pytest -q",
                'GET /readonly-e2e returns HTTP 200 and exactly {"readonly_e2e": true}',
                "product commit SHA equals product remote main SHA",
            ],
            "commit_message": "feat(api): add readonly e2e endpoint",
            "notes": ["Submitted through ORIS public Web console after Codex authentication recovery."],
        }
        submit_code, submitted = public_request(
            "POST",
            "/api/goals",
            username=username,
            password=password,
            console_token=console_token,
            body=payload,
            timeout=60,
        )
        state["PUBLIC_SUBMIT_HTTP"] = str(submit_code)
        paths["submit"].write_text(json.dumps(submitted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"PUBLIC_SUBMIT_HTTP={submit_code}")
        returned_id = submitted.get("task_id") if isinstance(submitted, dict) else None
        if submit_code != 201 or returned_id != task_id or submitted.get("status") != "queued":
            raise RuntimeError("public_goal_submission_failed")
        state["REAL_PRODUCT_TASK_SUBMITTED"] = "YES"

        log("===== poll terminal state and evidence =====")
        for attempt in range(1, 181):
            code, body = public_request(
                "GET",
                f"/api/goals/{task_id}",
                username=username,
                password=password,
                console_token=console_token,
            )
            if isinstance(body, dict):
                status_payload = body
            raw = str(status_payload.get("status") or "unknown")
            canonical = str(status_payload.get("canonical_status") or raw)
            terminal = status_payload.get("terminal") is True
            ready = evidence_ready(status_payload)
            log(
                f"POLL={attempt} HTTP={code} STATUS={raw} CANONICAL={canonical} "
                f"TERMINAL={'true' if terminal else 'false'} EVIDENCE_READY={'true' if ready else 'false'}"
            )
            if terminal and canonical != "completed":
                break
            if terminal and canonical == "completed" and ready:
                break
            time.sleep(10)
        else:
            raise RuntimeError("task_or_evidence_timeout")

        password = ""
        console_token = ""
        paths["status"].write_text(json.dumps(status_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        state["FINAL_STATUS"] = str(status_payload.get("status") or "unknown")
        state["CANONICAL_STATUS"] = str(status_payload.get("canonical_status") or state["FINAL_STATUS"])
        state["TERMINAL"] = "true" if status_payload.get("terminal") is True else "false"
        state["FAILURE_CODE"] = str(status_payload.get("failure_code") or "")
        if state["CANONICAL_STATUS"] != "completed" or not evidence_ready(status_payload):
            raise RuntimeError(f"task_not_completed_with_evidence:{state['CANONICAL_STATUS']}:{state['FAILURE_CODE']}")

        python_bin = PRODUCT / ".venv/bin/python"
        compile_result = proc([str(python_bin), "-m", "py_compile", "app/main.py"], cwd=PRODUCT, timeout=120)
        save_process(paths["py_compile"], compile_result)
        state["PRODUCT_PY_COMPILE"] = "PASS" if compile_result.returncode == 0 else "FAILED"
        if compile_result.returncode != 0:
            raise RuntimeError("product_py_compile_failed")
        pytest_result = proc([str(python_bin), "-m", "pytest", "-q"], cwd=PRODUCT, timeout=600)
        save_process(paths["pytest"], pytest_result)
        state["PRODUCT_PYTEST"] = "PASS" if pytest_result.returncode == 0 else "FAILED"
        if pytest_result.returncode != 0:
            raise RuntimeError("product_pytest_failed")
        after = endpoint_probe(paths["endpoint"])
        state["ENDPOINT_CONTRACT"] = "PASS" if after.get("exact") is True else "FAILED"
        if after.get("exact") is not True:
            raise RuntimeError("endpoint_contract_failed")

        local_head = command_output(["git", "rev-parse", "HEAD"], PRODUCT)
        remote_line = command_output(["git", "ls-remote", "origin", "refs/heads/main"], PRODUCT)
        remote_main = remote_line.split()[0] if remote_line else ""
        tracked_after = command_output(["git", "status", "--porcelain", "--untracked-files=no"], PRODUCT)
        state["PRODUCT_LOCAL_HEAD"] = local_head
        state["PRODUCT_REMOTE_MAIN"] = remote_main
        state["PRODUCT_CHANGED"] = "YES" if local_head != baseline else "NO"
        state["PRODUCT_WORKTREE_CLEAN"] = "YES" if not tracked_after else "NO"

        evidence = status_payload.get("github_evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        state["PRODUCT_COMMIT_SHA"] = str(evidence.get("product_commit_sha") or "")
        state["PRODUCT_REMOTE_SHA"] = str(evidence.get("product_remote_sha") or "")
        state["ORIS_EVIDENCE_COMMIT_SHA"] = str(evidence.get("oris_evidence_commit_sha") or "")
        state["ORIS_EVIDENCE_REMOTE_SHA"] = str(evidence.get("oris_evidence_remote_sha") or "")
        done_data = completed_done_record(status_payload)
        index_result = done_data.get("oris_evidence_index_result") if isinstance(done_data.get("oris_evidence_index_result"), dict) else {}
        state["ORIS_EVIDENCE_INDEX_COMMIT_SHA"] = str(index_result.get("commit_sha") or "")
        state["STRICT_RESULT_SCHEMA"] = "PASS" if evidence.get("strict_result_schema") is True else "FAILED"
        files = evidence.get("files") if isinstance(evidence.get("files"), list) else []
        labels = {str(item.get("label")) for item in files if isinstance(item, dict)}
        state["HOST_PYTEST_EVIDENCE"] = "PASS" if "host_pytest_log" in labels else "FAILED"

        product_shas = [state["PRODUCT_COMMIT_SHA"], state["PRODUCT_REMOTE_SHA"], local_head, remote_main]
        state["PRODUCT_SHA_MATCH"] = "YES" if all(product_shas) and len(set(product_shas)) == 1 else "NO"
        for key, expected in [
            ("PRODUCT_CHANGED", "YES"),
            ("PRODUCT_WORKTREE_CLEAN", "YES"),
            ("PRODUCT_SHA_MATCH", "YES"),
            ("HOST_PYTEST_EVIDENCE", "PASS"),
            ("STRICT_RESULT_SCHEMA", "PASS"),
        ]:
            if state[key] != expected:
                raise RuntimeError(f"verification_failed:{key}:{state[key]}")

        evidence_sha = state["ORIS_EVIDENCE_COMMIT_SHA"]
        evidence_remote = state["ORIS_EVIDENCE_REMOTE_SHA"]
        index_sha = state["ORIS_EVIDENCE_INDEX_COMMIT_SHA"]
        if not evidence_sha or not evidence_remote or not index_sha:
            raise RuntimeError("oris_evidence_sha_missing")
        if evidence_sha != evidence_remote:
            raise RuntimeError("oris_evidence_commit_remote_mismatch")
        fetched = proc(["git", "fetch", "origin", "main"], cwd=ORIS, timeout=180)
        if fetched.returncode != 0:
            raise RuntimeError("oris_fetch_failed")
        evidence_ancestor = proc(["git", "merge-base", "--is-ancestor", evidence_sha, "origin/main"], cwd=ORIS)
        index_ancestor = proc(["git", "merge-base", "--is-ancestor", index_sha, "origin/main"], cwd=ORIS)
        state["ORIS_EVIDENCE_ON_REMOTE"] = "YES" if evidence_ancestor.returncode == 0 else "NO"
        state["ORIS_INDEX_ON_REMOTE"] = "YES" if index_ancestor.returncode == 0 else "NO"
        if state["ORIS_EVIDENCE_ON_REMOTE"] != "YES" or state["ORIS_INDEX_ON_REMOTE"] != "YES":
            raise RuntimeError("oris_evidence_or_index_not_on_remote")

        state["RESULT"] = "PASS"
        state["NEXT_ACTION"] = "FINAL_ACCEPTANCE_COMPLETE"

    except Exception as exc:
        if not state["FAILURE_CODE"]:
            state["FAILURE_CODE"] = str(exc).splitlines()[0][:400]
        state["RESULT"] = "FAILED"
        state["NEXT_ACTION"] = "INSPECT_GITHUB_EVIDENCE"
        log(f"ERROR_CLASS={type(exc).__name__}")
        log(f"ERROR_SAFE={state['FAILURE_CODE']}")
    finally:
        password = ""
        console_token = ""
        state["CHECKED_AT"] = now_iso()
        state["PUBLIC_ENTRY"] = PUBLIC
        state["PRODUCT_REPO"] = PRODUCT_REPO
        for output_name, service in SERVICES.items():
            state[output_name] = service_state(service)

        log("===== verification =====")
        for key in [
            "RESULT", "FINAL_STATUS", "CANONICAL_STATUS", "TERMINAL", "FAILURE_CODE",
            "PRODUCT_PY_COMPILE", "PRODUCT_PYTEST", "ENDPOINT_CONTRACT",
            "HOST_PYTEST_EVIDENCE", "STRICT_RESULT_SCHEMA", "BASELINE_PRODUCT_SHA",
            "PRODUCT_COMMIT_SHA", "PRODUCT_REMOTE_SHA", "PRODUCT_LOCAL_HEAD",
            "PRODUCT_REMOTE_MAIN", "PRODUCT_SHA_MATCH", "PRODUCT_CHANGED",
            "PRODUCT_WORKTREE_CLEAN", "ORIS_EVIDENCE_COMMIT_SHA",
            "ORIS_EVIDENCE_REMOTE_SHA", "ORIS_EVIDENCE_INDEX_COMMIT_SHA",
            "ORIS_EVIDENCE_ON_REMOTE", "ORIS_INDEX_ON_REMOTE",
        ]:
            log(f"{key}={state[key]}")
        paths["main"].write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths["verification"].write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        commit_paths = [path for path in paths.values() if path.is_file()]
        state["LOG_COMMIT"] = git_commit_logs(
            commit_paths,
            f"test(dev-employee): verify public readonly E2E {task_id}",
        )
        if state["LOG_COMMIT"] in {
            "NO_LOG_FILES", "LOG_ADD_FAILED", "LOG_DIFF_FAILED", "LOG_COMMIT_FAILED", "LOG_PUSH_FAILED"
        }:
            state["RESULT"] = "FAILED"
            state["FAILURE_CODE"] = state["FAILURE_CODE"] or state["LOG_COMMIT"].lower()
            state["NEXT_ACTION"] = "RESOLVE_ORIS_EVIDENCE_PUSH"

        print()
        print("===== SUMMARY =====")
        for key in [
            "RESULT", "TASK_ID", "PUBLIC_SUBMIT_HTTP", "FINAL_STATUS", "CANONICAL_STATUS",
            "TERMINAL", "FAILURE_CODE", "PRODUCT_PY_COMPILE", "PRODUCT_PYTEST",
            "ENDPOINT_CONTRACT", "HOST_PYTEST_EVIDENCE", "STRICT_RESULT_SCHEMA",
            "BASELINE_PRODUCT_SHA", "PRODUCT_COMMIT_SHA", "PRODUCT_REMOTE_SHA",
            "PRODUCT_LOCAL_HEAD", "PRODUCT_REMOTE_MAIN", "PRODUCT_SHA_MATCH",
            "PRODUCT_CHANGED", "PRODUCT_WORKTREE_CLEAN", "ORIS_EVIDENCE_COMMIT_SHA",
            "ORIS_EVIDENCE_REMOTE_SHA", "ORIS_EVIDENCE_INDEX_COMMIT_SHA",
            "ORIS_EVIDENCE_ON_REMOTE", "ORIS_INDEX_ON_REMOTE", "LOG_COMMIT",
            "WEB_CONSOLE_SERVICE", "INTAKE_SERVICE", "BRIDGE_SERVICE",
            "REAL_PRODUCT_TASK_SUBMITTED", "NEXT_ACTION",
        ]:
            print(f"{key}={state[key]}")
        print(f"PUBLIC_ENTRY={PUBLIC}")
        print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
        print("===== END SUMMARY =====")

    return 0 if state["RESULT"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
