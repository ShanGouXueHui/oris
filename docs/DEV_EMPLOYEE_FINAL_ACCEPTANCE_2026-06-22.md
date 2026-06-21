# ORIS Dev Employee Final Acceptance — 2026-06-22

## Verdict

Final acceptance passed.

The ORIS / OpenClaw / Codex-backed AI Dev Employee main execution loop is validated end-to-end for the FastAPI task-board demo project.

## Acceptance sample

- Task ID: `demo-openclaw-web-task-board-20260622015615`
- Product repository: `ShanGouXueHui/oris-final-acceptance-api`
- Product local path: `/home/admin/projects/oris-final-acceptance-api`
- Product commit SHA: `9ccff8fcef6eb8ef08597183eb16fb235f1f7b59`
- ORIS evidence commit SHA: `89d54bb945013048366b53805d1ff3d027fbfe55`
- Evidence index final commit SHA: `eaccdec3acefa794283a5c67b34280d241507a01`

## Final verifier result

```json
{
  "status_accept": true,
  "terminal": true,
  "has_product_commit_sha": true,
  "has_evidence_files": true,
  "product_commit_sha": "9ccff8fcef6eb8ef08597183eb16fb235f1f7b59"
}
```

## Validated execution path

```text
OpenClaw / ORIS task intake
  -> ORIS queue / status API
  -> supervised bridge
  -> Codex CLI real execution
  -> product repository verification
  -> product commit SHA capture
  -> ORIS evidence files generation
  -> ORIS evidence commit and push
  -> status API terminal=true
  -> verifier acceptance=true
```

## Product verification

The product repository already contained the requested implementation by the final accepted run:

- `GET /healthz/details` exists in `app/main.py`.
- Pytest coverage exists in `tests/test_tasks_api.py`.
- Host final checks passed:
  - `compileall`: pass
  - `pytest -q`: 28 passed
  - `pytest -q -W error`: 28 passed

The product repository was clean during the accepted Codex run, so the bridge captured the existing product HEAD SHA as the product commit SHA.

## Evidence files

The accepted ORIS run generated and committed evidence including:

- `orchestration/task_runs/demo-openclaw-web-task-board-20260622015615.json`
- `orchestration/task_runs/demo-openclaw-web-task-board-20260622015615.codex_result.json`
- `logs/dev_employee/latest_task_progress.json`
- `logs/dev_employee/demo-openclaw-web-task-board-20260622015615.codex.log`
- `logs/dev_employee/demo-openclaw-web-task-board-20260622015615_host_py_compile.txt`
- `logs/dev_employee/demo-openclaw-web-task-board-20260622015615_host_pytest.txt`
- `logs/dev_employee/demo-openclaw-web-task-board-20260622015615_host_pytest_werror.txt`
- `logs/dev_employee/skill_resolution/demo-openclaw-web-task-board-20260622015615.json`
- `logs/dev_employee/skill_resolution/demo-openclaw-web-task-board-20260622015615.md`
- `logs/dev_employee/evidence_commit_index/demo-openclaw-web-task-board-20260622015615.json`

## Defects fixed during acceptance

The following issues were discovered and fixed during acceptance:

1. Stale-running tasks could remain non-terminal after unhandled bridge exceptions.
2. ORIS evidence files under ignored runtime directories required bounded `git add -f`.
3. `run_codex_auth_preflight()` required explicit `codex_bin` and `workdir` arguments.
4. Intake descriptors using `expected_product_path` needed normalization to `product_path`.
5. Codex CLI 0.133.0 rejected `codex exec --cwd`; subprocess cwd is now used instead.
6. Codex sandbox needed ORIS evidence directory write access via `--add-dir`.
7. Runtime result prompt needed alignment with `dev_employee_result_validator.py`.
8. `success` and `done` needed terminal classification as canonical `completed`.
9. Compatibility exports were restored for `dev_employee_queue_kernel.py` and `dev_employee_intake_api.py`.

## Operational rule after acceptance

Do not rerun fresh demo tasks for this acceptance sample unless intentionally testing a new regression. Use the accepted task ID for status/API/UI verification:

```bash
cd /home/admin/projects/oris
bash runbooks/oris_demo_verify_openclaw_result.sh demo-openclaw-web-task-board-20260622015615
```

Expected final verdict remains:

```json
{
  "status_accept": true,
  "terminal": true,
  "has_product_commit_sha": true,
  "has_evidence_files": true
}
```
