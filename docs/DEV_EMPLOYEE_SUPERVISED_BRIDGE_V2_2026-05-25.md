# ORIS Dev Employee Supervised Bridge v2 — 2026-05-25

## Goal

Bridge v1 proved the chain:

```text
queued task descriptor -> bridge claim -> Codex CLI process -> real sandbox command execution -> log output
```

Bridge v2 upgrades this into a supervised completion system.

## Core change

Codex no longer owns GitHub push or remote verification when sandbox networking is restricted.

Instead:

1. Codex performs local code changes and local checks.
2. Codex writes a structured result file under ORIS task runs.
3. The outer host bridge reads that result file.
4. The outer host bridge performs final checks, product commit/push, remote verification, ORIS evidence update, and ORIS commit/push.

## Responsibility split

### Codex inside sandbox

Allowed:

- read required ORIS context;
- edit product repo files inside the product repo;
- run local tests and write logs;
- write `orchestration/task_runs/<task_id>.codex_result.json`.

Forbidden:

- claiming final completion without outer bridge verification;
- relying on GitHub push from sandbox;
- writing product implementation into ORIS repo;
- committing secrets, venv, caches, or runtime noise.

### Outer bridge on host

Required:

- claim queued task;
- invoke Codex CLI;
- read Codex structured result;
- rerun final checks outside Codex;
- commit/push product repo;
- verify product remote head;
- write ORIS evidence logs/state;
- commit/push ORIS evidence;
- mark task completed only after remote evidence is verified.

## Result contract

Codex must write JSON similar to:

```json
{
  "task_id": "formal-test-pydantic-cleanup-v2-20260525",
  "status": "local_checks_passed",
  "product_path": "/home/admin/projects/oris-final-acceptance-api",
  "changed_files": ["app/main.py"],
  "check_logs": {
    "py_compile": "/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_py_compile_20260525.txt",
    "pytest": "/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_pytest_20260525.txt",
    "pytest_werror": "/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_pytest_werror_20260525.txt"
  },
  "notes": "Local checks passed; outer bridge must commit, push, and verify remote."
}
```

## Completion criteria

A supervised bridge task is completed only if:

1. Codex exits with return code 0;
2. result file exists and has `status=local_checks_passed`;
3. outer bridge reruns all final checks successfully;
4. product repo has a real commit SHA;
5. product commit is pushed to GitHub main;
6. `git ls-remote origin main` matches the product commit;
7. ORIS evidence files record the product commit, checks, and remote verification;
8. ORIS evidence commit is pushed to GitHub main.

## Immediate test target

Use Pydantic v2 cleanup as the formal bridge-v2 test because it is small, deterministic, and has a strict no-warning gate:

```bash
PYTHONPATH=/home/admin/projects/oris-final-acceptance-api python -m pytest -q -W error::DeprecationWarning
```
