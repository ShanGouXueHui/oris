# ORIS Dev Employee Final Acceptance Retrospective — 2026-05-24

## Result

Final acceptance for `oris-final-acceptance-api` is complete.

- Product repository: `https://github.com/ShanGouXueHui/oris-final-acceptance-api`
- Product commit: `8f74b23728904889c2b075f0aae48c44165549ae`
- ORIS evidence commit: `87575cc686f57650252f1fb4353e0403d42dbd93`
- Final pytest evidence: `8 passed, 8 warnings in 0.29s`
- Product code location: `/home/admin/projects/oris-final-acceptance-api`
- ORIS product-code boundary: preserved; no product implementation was placed in `/home/admin/projects/oris`.

## What was validated

The final acceptance flow validated that the ORIS AI Dev Employee can:

1. read GitHub-backed durable context;
2. generate an independent FastAPI project through Codex CLI;
3. create product implementation and tests in a separate repository;
4. produce a real local product commit;
5. push the product repository to GitHub;
6. update ORIS project registry and durable task state;
7. preserve verifiable command evidence in GitHub logs.

## Important defects found and fixed

### 1. OpenClaw-style pseudo execution is not acceptable

The task cannot be considered complete from planner text or pseudo `exec/write` output. Real evidence must come from host filesystem execution, command output, Git commit SHA, and GitHub remote state.

### 2. Codex sandbox may not have network/DNS

The Codex run created the product code and local commit, but push failed inside Codex sandbox due DNS resolution of `github.com`. Push and GitHub repo creation should be performed by the outer host shell when Codex sandbox networking is unavailable.

### 3. Test dependency environment must be explicit

Initial pytest execution failed because `pytest` was not installed in the active product environment. The repair flow now creates/uses `.venv` and installs `requirements.txt` before running checks.

### 4. Python package import path must be stable

Initial pytest evidence failed with `ModuleNotFoundError: No module named 'app'`. The product repo was fixed by adding `app/__init__.py`, and the evidence refresh flow runs tests with `PYTHONPATH` pointing to the product repository.

### 5. ORIS reset can destroy freshly generated logs

A previous evidence refresh wrote logs under ORIS, then reset ORIS to `origin/main`, causing the old failed pytest log to remain. The corrected pattern writes fresh evidence to `/tmp` first, resets ORIS, then copies evidence back into `logs/dev_employee/` before committing.

### 6. Local ORIS main must track remote before pushing

A non-fast-forward push occurred because the local ORIS branch was behind remote. The corrected pattern uses `git fetch origin main` and `git reset --hard origin/main` before applying evidence and registry updates.

## Policy updates to carry forward

For future AI Dev Employee tasks:

- Always separate Codex code generation from outer-shell GitHub push when sandbox networking is uncertain.
- Write transient test evidence to `/tmp` before any repository reset.
- Use project `.venv` and install `requirements.txt` before tests.
- Use `PYTHONPATH=<project_root>` for package-style FastAPI tests unless the project has packaging metadata.
- Do not mark task state as `completed` until passing test logs are committed in ORIS.
- Verify GitHub evidence after push; do not rely only on terminal output.
- Keep runtime noise uncommitted unless the user explicitly asks to archive it.

## Remaining non-blocking improvement

The final product tests pass but emit Pydantic v2 deprecation warnings. This is not a final-acceptance blocker. A later cleanup can replace class-based Pydantic config and `.dict()` calls with Pydantic v2 APIs, then refresh evidence.
