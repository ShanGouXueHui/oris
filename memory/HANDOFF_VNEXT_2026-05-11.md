# ORIS vNext Handoff — 2026-05-11

## Current status

Dev Employee Phase 2 scaffold is now present in the repository.

This handoff is intentionally separate from the large historical `memory/HANDOFF.md` file to avoid overwriting long accumulated runtime memory. Future sessions should read this file immediately after the existing handoff when working on ORIS vNext.

## Files added in this step

- `config/dev_employee_runtime.json`
- `oris_vnext/__init__.py`
- `oris_vnext/task_kernel.py`
- `oris_vnext/codex_executor.py`
- `oris_vnext/validation.py`
- `scripts/dev_employee_smoke.py`
- `docs/DEV_EMPLOYEE_PHASE2_SCAFFOLD.md`
- `docs/PROJECT_STATE_VNEXT_2026-05-11.md`
- `logs/dev_employee/20260511/phase2_scaffold.summary.md`

## Current runtime chain

```text
OpenClaw access/channel layer
  -> ORIS Native Task Kernel
  -> Worker Registry / Dev Employee profile
  -> Execution Ledger
  -> CodexExecutor dry-run contract
  -> Validation Pipeline
  -> GitHub docs/log handoff
```

## Important constraints

- OpenClaw remains the access layer.
- ORIS Native Task Kernel becomes the Dev Employee orchestration layer.
- Real Codex execution remains disabled by default.
- Channel handlers must enqueue or hand off; they should not run long tasks directly.
- Stable rules live in `config/`.
- Secrets remain env/secrets only.
- No `set -e` in user-facing shell flows.
- Provider orchestration is reused, not rewritten.

## Validation performed before commit

```bash
python3 -m compileall -q /mnt/data/oris_scaffold/oris_vnext /mnt/data/oris_scaffold/scripts/dev_employee_smoke.py
cd /mnt/data/oris_scaffold && python3 scripts/dev_employee_smoke.py --dry-run
```

Observed smoke output contained:

```json
{
  "ok": true,
  "worker_profile": "dev_employee",
  "model_role": "coding_planning",
  "codex_dry_run": true
}
```

## Next recommended step

Implement the repo bootstrap reader first. It should verify all `required_bootstrap_docs` in `config/dev_employee_runtime.json` exist before the Dev Employee plans or executes code changes.

After that, add approval-gated real Codex execution and validation report promotion to `logs/dev_employee/YYYYMMDD/`.
