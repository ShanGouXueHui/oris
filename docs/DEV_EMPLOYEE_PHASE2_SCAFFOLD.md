# Dev Employee Phase 2 Scaffold

Date: 2026-05-11

## Scope

This scaffold implements the first ORIS vNext Dev Employee coding baseline:

- Task Kernel scaffold
- Worker Registry
- DevTask schema
- Execution Ledger contract
- CodexExecutor dry-run command contract
- Validation Pipeline contract
- GitHub-oriented log summary convention through config

It does not replace OpenClaw. OpenClaw remains the access and channel layer.
It does not implement a second provider system. Model roles continue to map into the existing provider orchestration policy.

## Files

- `config/dev_employee_runtime.json`
- `oris_vnext/task_kernel.py`
- `oris_vnext/codex_executor.py`
- `oris_vnext/validation.py`
- `scripts/dev_employee_smoke.py`

## Runtime contract

Channel handlers should not execute long-running work directly. They should create or enqueue a task through the ORIS-native Task Kernel.

The first supported task type is `dev_task`. The default worker is `dev_employee`.

The Task Kernel creates a `task_run` record and appends it to the JSONL execution ledger configured in `config/dev_employee_runtime.json`.

## CodexExecutor contract

`CodexExecutor` is dry-run by default. It establishes:

- command construction
- prompt validation
- forbidden shell fragment guard
- stdout/stderr log paths for future real execution
- JSON result shape for ledger attachment

Real Codex execution should be enabled only after the dry-run contract, validation pipeline, and write approval gates are stable.

## Validation

Run from the repository root:

```bash
python3 -m compileall -q oris_vnext scripts/dev_employee_smoke.py
python3 scripts/dev_employee_smoke.py --dry-run
```

Expected result:

- Python compile succeeds
- smoke script prints a JSON object with `ok: true`
- runtime artifacts are written under `run/dev_employee/`

## Next step

The next implementation should connect this scaffold to the real local repository runtime:

1. add a repo bootstrap reader that verifies required docs exist before planning;
2. add a validation runner that writes summary artifacts into `logs/dev_employee/YYYYMMDD/` only when decision-useful;
3. add an approval-gated Codex execution path;
4. update docs and handoff after each validated change.
