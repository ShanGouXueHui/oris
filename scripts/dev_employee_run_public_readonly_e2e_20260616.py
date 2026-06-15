#!/usr/bin/env python3
"""Run the final public Web -> Codex -> product -> GitHub acceptance flow.

Secrets are kept in memory only. The script never writes Basic Auth credentials,
Console Tokens, authorization headers, or raw request objects to logs.
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

ORIS_DIR = Path("/home/admin/projects/oris")
PRODUCT_DIR = Path("/home/admin/projects/oris-final-acceptance-api")
ENV_FILE = Path.home() / ".config/oris/dev_employee_enqueue.env"
PUBLIC_BASE = "https://control.orisfy.com"
PROJECT_KEY = "oris-final-acceptance-api"
PRODUCT_REPO = "ShanGouXueHui/oris-final-acceptance-api"
HARDENING_COMMIT = "57cf6eccb1bbf7cc4e6ddd79eab94e7530d3fe5c"
SERVICES = {
    "web_console": "oris-dev-employee-web-console.service",
    "intake": "oris-dev-employee-intake.service",
    "bridge": "oris-dev-employee-bridge.service",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def read_env_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 300,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def git_output(cwd: Path, *args: str) -> str:
    proc = run(["git", *args], cwd=cwd, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()[-1000:]}")
    return proc.stdout.strip()


def service_state(name: str) -> str:
    proc = run(["systemctl", "--user", "is-active", name], timeout=30)
    return (proc.stdout or proc.stderr).strip() or "unknown"


def public_request(
    method: str,
    path: str,
    *,
    basic_user: str | None = None,
    basic_password: str | None = None,
    console_token: str | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 45,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if basic_user is not None and basic_password is not None:
        credential = base64.b64encode(f"{basic_user}:{basic_password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {credential}"
    if console_token:
        headers["X-ORIS-Console-Token"] = console_token
    request = urllib.request.Request(PUBLIC_BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw[:4000]}
            return response.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:4000]}
        return exc.code, payload
    except urllib.error.URLError as exc:
        return 599, {"error": "url_error", "message": str(exc.reason)}


def exact_endpoint_probe(output_path: Path) -> tuple[bool, dict[str, Any]]:
    python_bin = PRODUCT_DIR / ".venv/bin/python"
    code = r'''
import json
from fastapi.testclient import TestClient
from app.main import app

response = TestClient(app).get("/readonly-e2e")
try:
    body = response.json()
except Exception:
    body = response.text
result = {
    "status_code": response.status_code,
    "body": body,
    "exact": response.status_code == 200 and body == {"readonly_e2e": True},
}
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
'''
    proc = run([str(python_bin), "-c", code], cwd=PRODUCT_DIR, timeout=120)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode != 0:
        return False, {"return_code": proc.returncode, "error": (proc.stderr or proc.stdout)[-2000:]}
    try:
        payload = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except Exception as exc:
        return False, {"return_code": proc.returncode, "error": type(exc).__name__}
    return bool(payload.get("exact")), payload


def write_process_output(path: Path, proc: subprocess.CompletedProcess[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"return_code={proc.returncode}\n\n===== stdout =====\n{proc.stdout or ''}\n===== stderr =====\n{proc.stderr or ''}\n",
        encoding="utf-8",
    )


def main() -> int:
    task_id = f"goal-{PROJECT_KEY}-readonly-e2e-{stamp()}"
    run_stamp = stamp()
    log_dir = ORIS_DIR / "logs/dev_employee/web_console_public_submit_e2e"
    log_dir.mkdir(parents=True, exist_ok=True)
    main_log = log_dir / f"{task_id}.final-acceptance.log"
    submit_json = log_dir / f"{task_id}.submit.json"
    status_json = log_dir / f"{task_id}.status.json"
    verify_json = log_dir / f"{task_id}.verification.json"
    py_compile_log = log_dir / f"{task_id}.product-py-compile.txt"
    pytest_log = log_dir / f"{task_id}.product-pytest.txt"
    endpoint_log = log_dir / f"{task_id}.endpoint-contract.txt"

    state: dict[str, Any] = {
        "result": "FAILED",
        "task_id": task_id,
        "public_submit_http": None,
        "final_status": "unknown",
        "canonical_status": "unknown",
        "terminal": False,
        "failure_code": "",
        "product_py_compile": "NOT_RUN",
        "product_pytest": "NOT_RUN",
        "endpoint_contract": "NOT_RUN",
        "host_pytest_evidence": "NOT_VERIFIED",
        "strict_result_schema": "NOT_VERIFIED",
        "baseline_product_sha": "",
        "product_commit_sha": "",
        "product_remote_sha": "",
        "product_local_head": "",
        "product_remote_main": "",
        "product_sha_match": "NO",
        "product_changed": "NO",
        "product_worktree_clean": "NO",
        "oris_evidence_commit_sha": "",
        "oris_evidence_remote_sha": "",
        "oris_evidence_on_remote": "NO",
        "log_commit": "",
        "next_action": "INSPECT_GITHUB_EVIDENCE",
    }
    safe_log_lines: list[str] = []

    def log(message: str = "") -> None:
        safe_log_lines.append(message)
        print(message, flush=True)

    def persist_safe_log() -> None:
        main_log.write_text("\n".join(safe_log_lines) + "\n", encoding="utf-8")

    basic_user = ""
    basic_password = ""
    console_token = ""
    status_payload: dict[str, Any] = {}

    try:
        if os.geteuid() == 0 or getpass.getuser() != "admin":
            raise RuntimeError("wrong_linux_user")
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise RuntimeError("interactive_tty_required")
        if not ORIS_DIR.is_dir() or not PRODUCT_DIR.is_dir():
            raise RuntimeError("required_repository_missing")

        log("===== timestamp =====")
        log(now_iso())
        log("===== task =====")
        log(f"TASK_ID={task_id}")
        log(f"PROJECT_KEY={PROJECT_KEY}")
        log(f"PUBLIC_ENTRY={PUBLIC_BASE}")

        for label, service in SERVICES.items():
            current = service_state(service)
            log(f"SERVICE_{label.upper()}={current}")
            if current != "active":
                raise RuntimeError(f"service_not_active:{service}")

        if run(["git", "merge-base", "--is-ancestor", HARDENING_COMMIT, "HEAD"], cwd=ORIS_DIR).returncode != 0:
            raise RuntimeError("hardening_commit_not_present")

        product_python = PRODUCT_DIR / ".venv/bin/python"
        if not product_python.is_file():
            raise RuntimeError("product_venv_missing")

        tracked_dirty = git_output(PRODUCT_DIR, "status", "--porcelain", "--untracked-files=no")
        if tracked_dirty:
            raise RuntimeError("product_tracked_worktree_dirty")
        baseline_sha = git_output(PRODUCT_DIR, "rev-parse", "HEAD")
        baseline_remote = git_output(PRODUCT_DIR, "ls-remote", "origin", "refs/heads/main").split()[0]
        state["baseline_product_sha"] = baseline_sha
        log(f"BASELINE_PRODUCT_SHA={baseline_sha}")
        log(f"BASELINE_PRODUCT_REMOTE_SHA={baseline_remote}")
        if baseline_sha != baseline_remote:
            raise RuntimeError("product_baseline_remote_sha_mismatch")

        baseline_exact, baseline_probe = exact_endpoint_probe(endpoint_log)
        log(f"BASELINE_ENDPOINT_STATUS={baseline_probe.get('status_code', 'probe_failed')}")
        log(f"BASELINE_ENDPOINT_EXACT={'yes' if baseline_exact else 'no'}")
        if baseline_exact:
            raise RuntimeError("readonly_e2e_already_present_before_new_task")

        console_token = read_env_value(ENV_FILE, "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN")
        if not console_token:
            raise RuntimeError("console_token_missing")

        basic_user = input("Public Basic Auth username: ").strip()
        basic_password = getpass.getpass("Public Basic Auth password: ")
        if not basic_user or not basic_password:
            raise RuntimeError("public_basic_auth_missing")

        unauth_code, _ = public_request("GET", "/health")
        log(f"PUBLIC_UNAUTH_HEALTH_HTTP={unauth_code}")
        if unauth_code != 401:
            raise RuntimeError("public_basic_auth_boundary_not_enforced")

        health_code, health_payload = public_request(
            "GET",
            "/health",
            basic_user=basic_user,
            basic_password=basic_password,
        )
        log(f"PUBLIC_AUTH_HEALTH_HTTP={health_code}")
        if health_code != 200 or health_payload.get("status") != "ok":
            raise RuntimeError("public_authenticated_health_failed")

        projects_code, projects_payload = public_request(
            "GET",
            "/api/projects",
            basic_user=basic_user,
            basic_password=basic_password,
            console_token=console_token,
        )
        projects = projects_payload.get("projects") if isinstance(projects_payload, dict) else None
        log(f"PUBLIC_PROJECTS_HTTP={projects_code}")
        log(f"PROJECT_ALLOWLIST_MATCH={'yes' if isinstance(projects, list) and projects == [PROJECT_KEY] else 'no'}")
        if projects_code != 200 or not isinstance(projects, list) or PROJECT_KEY not in projects:
            raise RuntimeError("public_project_allowlist_validation_failed")

        objective = (
            'Add a minimal FastAPI GET /readonly-e2e endpoint that returns exactly '
            '{"readonly_e2e": true}. Add pytest coverage for the status code and exact JSON response. '
            "Run the complete existing test suite, commit the product changes to main, push them to the configured "
            "GitHub remote, and emit strict structured evidence with the product commit SHA and remote SHA."
        )
        payload = {
            "task_id": task_id,
            "project_key": PROJECT_KEY,
            "objective": objective,
            "constraints": [
                "Modify only the standalone product repository; do not place product code in the ORIS repository.",
                "Preserve all existing task-board API behavior and public contracts.",
                "Use the existing FastAPI application and pytest conventions.",
                "Keep the implementation minimal and deterministic.",
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

        submit_code, submit_payload = public_request(
            "POST",
            "/api/goals",
            basic_user=basic_user,
            basic_password=basic_password,
            console_token=console_token,
            body=payload,
            timeout=60,
        )
        state["public_submit_http"] = submit_code
        submit_json.write_text(json.dumps(submit_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"PUBLIC_SUBMIT_HTTP={submit_code}")
        returned_task_id = submit_payload.get("task_id") if isinstance(submit_payload, dict) else None
        log(f"RETURNED_TASK_ID={returned_task_id or ''}")
        if submit_code != 201 or returned_task_id != task_id or submit_payload.get("status") != "queued":
            raise RuntimeError("public_goal_submission_failed")

        # Remove live credentials as soon as the public polling phase ends.
        log("REAL_PRODUCT_TASK_SUBMITTED=YES")
        log("===== poll terminal state =====")
        for attempt in range(1, 181):
            status_code, body = public_request(
                "GET",
                f"/api/goals/{task_id}",
                basic_user=basic_user,
                basic_password=basic_password,
                console_token=console_token,
                timeout=45,
            )
            if isinstance(body, dict):
                status_payload = body
            raw_status = str(status_payload.get("status") or "unknown")
            canonical = str(status_payload.get("canonical_status") or raw_status)
            terminal = status_payload.get("terminal") is True
            log(f"POLL={attempt} HTTP={status_code} STATUS={raw_status} CANONICAL={canonical} TERMINAL={'true' if terminal else 'false'}")
            if status_code == 200 and terminal:
                break
            time.sleep(10)
        else:
            raise RuntimeError("task_terminal_state_timeout")

        basic_password = ""
        console_token = ""

        status_json.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        state["final_status"] = str(status_payload.get("status") or "unknown")
        state["canonical_status"] = str(status_payload.get("canonical_status") or state["final_status"])
        state["terminal"] = status_payload.get("terminal") is True
        state["failure_code"] = str(status_payload.get("failure_code") or "")
        if state["canonical_status"] != "completed":
            raise RuntimeError(f"task_not_completed:{state['canonical_status']}:{state['failure_code']}")

        py_compile_proc = run(
            [str(product_python), "-m", "py_compile", "app/main.py"],
            cwd=PRODUCT_DIR,
            timeout=120,
        )
        write_process_output(py_compile_log, py_compile_proc)
        state["product_py_compile"] = "PASS" if py_compile_proc.returncode == 0 else "FAILED"
        if py_compile_proc.returncode != 0:
            raise RuntimeError("product_py_compile_failed")

        pytest_proc = run(
            [str(product_python), "-m", "pytest", "-q"],
            cwd=PRODUCT_DIR,
            timeout=600,
        )
        write_process_output(pytest_log, pytest_proc)
        state["product_pytest"] = "PASS" if pytest_proc.returncode == 0 else "FAILED"
        if pytest_proc.returncode != 0:
            raise RuntimeError("product_pytest_failed")

        exact, endpoint_payload = exact_endpoint_probe(endpoint_log)
        state["endpoint_contract"] = "PASS" if exact else "FAILED"
        if not exact:
            raise RuntimeError(f"endpoint_contract_failed:{endpoint_payload}")

        product_local = git_output(PRODUCT_DIR, "rev-parse", "HEAD")
        product_remote = git_output(PRODUCT_DIR, "ls-remote", "origin", "refs/heads/main").split()[0]
        tracked_dirty_after = git_output(PRODUCT_DIR, "status", "--porcelain", "--untracked-files=no")
        state["product_local_head"] = product_local
        state["product_remote_main"] = product_remote
        state["product_worktree_clean"] = "YES" if not tracked_dirty_after else "NO"
        state["product_changed"] = "YES" if product_local != baseline_sha else "NO"

        github_evidence = status_payload.get("github_evidence") if isinstance(status_payload.get("github_evidence"), dict) else {}
        state["product_commit_sha"] = str(github_evidence.get("product_commit_sha") or status_payload.get("product_commit_sha") or "")
        state["product_remote_sha"] = str(github_evidence.get("product_remote_sha") or status_payload.get("product_remote_sha") or "")
        state["oris_evidence_commit_sha"] = str(github_evidence.get("oris_evidence_commit_sha") or status_payload.get("oris_evidence_commit_sha") or "")
        state["oris_evidence_remote_sha"] = str(github_evidence.get("oris_evidence_remote_sha") or "")
        state["strict_result_schema"] = "PASS" if github_evidence.get("strict_result_schema") is True else "FAILED"

        evidence_files = github_evidence.get("files") if isinstance(github_evidence.get("files"), list) else []
        labels = {str(item.get("label")) for item in evidence_files if isinstance(item, dict)}
        state["host_pytest_evidence"] = "PASS" if "host_pytest_log" in labels else "FAILED"

        expected_product_sha = state["product_commit_sha"]
        expected_remote_sha = state["product_remote_sha"]
        sha_values = [expected_product_sha, expected_remote_sha, product_local, product_remote]
        state["product_sha_match"] = "YES" if all(sha_values) and len(set(sha_values)) == 1 else "NO"

        if state["product_changed"] != "YES":
            raise RuntimeError("product_commit_did_not_change")
        if state["product_worktree_clean"] != "YES":
            raise RuntimeError("product_worktree_not_clean_after_completion")
        if state["product_sha_match"] != "YES":
            raise RuntimeError("product_sha_mismatch")
        if state["host_pytest_evidence"] != "PASS":
            raise RuntimeError("host_pytest_evidence_missing")
        if state["strict_result_schema"] != "PASS":
            raise RuntimeError("strict_result_schema_not_verified")

        oris_evidence = state["oris_evidence_commit_sha"]
        if not oris_evidence:
            raise RuntimeError("oris_evidence_commit_missing")
        fetch_proc = run(["git", "fetch", "origin", "main"], cwd=ORIS_DIR, timeout=180)
        if fetch_proc.returncode != 0:
            raise RuntimeError("oris_fetch_failed")
        ancestor_proc = run(["git", "merge-base", "--is-ancestor", oris_evidence, "origin/main"], cwd=ORIS_DIR, timeout=60)
        state["oris_evidence_on_remote"] = "YES" if ancestor_proc.returncode == 0 else "NO"
        if state["oris_evidence_on_remote"] != "YES":
            raise RuntimeError("oris_evidence_not_on_remote_main")
        if state["oris_evidence_remote_sha"] and state["oris_evidence_remote_sha"] != oris_evidence:
            raise RuntimeError("oris_evidence_remote_sha_mismatch")

        state["result"] = "PASS"
        state["next_action"] = "FINAL_ACCEPTANCE_COMPLETE"

    except Exception as exc:
        if not state["failure_code"]:
            state["failure_code"] = str(exc).splitlines()[0][:300]
        state["result"] = "FAILED"
        state["next_action"] = "INSPECT_GITHUB_EVIDENCE"
        log(f"ERROR_CLASS={type(exc).__name__}")
        log(f"ERROR_SAFE={state['failure_code']}")
    finally:
        basic_password = ""
        console_token = ""

        state["services"] = {label: service_state(name) for label, name in SERVICES.items()}
        state["checked_at"] = now_iso()
        state["public_entry"] = PUBLIC_BASE
        state["product_repo"] = PRODUCT_REPO
        verify_json.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        log("===== verification =====")
        for key in [
            "result",
            "final_status",
            "canonical_status",
            "terminal",
            "failure_code",
            "product_py_compile",
            "product_pytest",
            "endpoint_contract",
            "host_pytest_evidence",
            "strict_result_schema",
            "baseline_product_sha",
            "product_commit_sha",
            "product_remote_sha",
            "product_local_head",
            "product_remote_main",
            "product_sha_match",
            "product_changed",
            "product_worktree_clean",
            "oris_evidence_commit_sha",
            "oris_evidence_remote_sha",
            "oris_evidence_on_remote",
        ]:
            log(f"{key.upper()}={state.get(key, '')}")
        persist_safe_log()

        files_to_commit = [path for path in [main_log, submit_json, status_json, verify_json, py_compile_log, pytest_log, endpoint_log] if path.exists()]
        if files_to_commit:
            add_proc = run(["git", "add", "--", *[str(path) for path in files_to_commit]], cwd=ORIS_DIR, timeout=120)
            if add_proc.returncode == 0:
                diff_proc = run(["git", "diff", "--cached", "--quiet", "--", *[str(path) for path in files_to_commit]], cwd=ORIS_DIR, timeout=60)
                if diff_proc.returncode == 1:
                    commit_proc = run(
                        ["git", "commit", "--only", "-m", f"test(dev-employee): verify public readonly E2E {task_id}", "--", *[str(path) for path in files_to_commit]],
                        cwd=ORIS_DIR,
                        timeout=180,
                    )
                    if commit_proc.returncode == 0:
                        push_proc = run(["git", "push", "origin", "main"], cwd=ORIS_DIR, timeout=180)
                        if push_proc.returncode == 0:
                            state["log_commit"] = git_output(ORIS_DIR, "rev-parse", "HEAD")
                        else:
                            state["log_commit"] = "LOG_PUSH_FAILED"
                            state["result"] = "FAILED"
                            state["failure_code"] = state["failure_code"] or "verification_log_push_failed"
                            state["next_action"] = "RESOLVE_ORIS_EVIDENCE_PUSH"
                    else:
                        state["log_commit"] = "LOG_COMMIT_FAILED"
                        state["result"] = "FAILED"
                        state["failure_code"] = state["failure_code"] or "verification_log_commit_failed"
                elif diff_proc.returncode == 0:
                    state["log_commit"] = "NO_LOG_CHANGES"
                else:
                    state["log_commit"] = "LOG_DIFF_CHECK_FAILED"
                    state["result"] = "FAILED"
            else:
                state["log_commit"] = "LOG_ADD_FAILED"
                state["result"] = "FAILED"

        print()
        print("===== SUMMARY =====")
        print(f"RESULT={state['result']}")
        print(f"TASK_ID={state['task_id']}")
        print(f"PUBLIC_SUBMIT_HTTP={state['public_submit_http'] if state['public_submit_http'] is not None else ''}")
        print(f"FINAL_STATUS={state['final_status']}")
        print(f"CANONICAL_STATUS={state['canonical_status']}")
        print(f"TERMINAL={'true' if state['terminal'] else 'false'}")
        print(f"FAILURE_CODE={state['failure_code']}")
        print(f"PRODUCT_PY_COMPILE={state['product_py_compile']}")
        print(f"PRODUCT_PYTEST={state['product_pytest']}")
        print(f"ENDPOINT_CONTRACT={state['endpoint_contract']}")
        print(f"HOST_PYTEST_EVIDENCE={state['host_pytest_evidence']}")
        print(f"STRICT_RESULT_SCHEMA={state['strict_result_schema']}")
        print(f"BASELINE_PRODUCT_SHA={state['baseline_product_sha']}")
        print(f"PRODUCT_COMMIT_SHA={state['product_commit_sha']}")
        print(f"PRODUCT_REMOTE_SHA={state['product_remote_sha']}")
        print(f"PRODUCT_LOCAL_HEAD={state['product_local_head']}")
        print(f"PRODUCT_REMOTE_MAIN={state['product_remote_main']}")
        print(f"PRODUCT_SHA_MATCH={state['product_sha_match']}")
        print(f"PRODUCT_CHANGED={state['product_changed']}")
        print(f"PRODUCT_WORKTREE_CLEAN={state['product_worktree_clean']}")
        print(f"ORIS_EVIDENCE_COMMIT_SHA={state['oris_evidence_commit_sha']}")
        print(f"ORIS_EVIDENCE_REMOTE_SHA={state['oris_evidence_remote_sha']}")
        print(f"ORIS_EVIDENCE_ON_REMOTE={state['oris_evidence_on_remote']}")
        print(f"LOG_COMMIT={state['log_commit']}")
        print(f"PUBLIC_ENTRY={PUBLIC_BASE}")
        print(f"WEB_CONSOLE_SERVICE={state['services']['web_console']}")
        print(f"INTAKE_SERVICE={state['services']['intake']}")
        print(f"BRIDGE_SERVICE={state['services']['bridge']}")
        print("REAL_PRODUCT_TASK_SUBMITTED=YES" if state["public_submit_http"] == 201 else "REAL_PRODUCT_TASK_SUBMITTED=NO")
        print(f"NEXT_ACTION={state['next_action']}")
        print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
        print("===== END SUMMARY =====")

    return 0 if state["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
