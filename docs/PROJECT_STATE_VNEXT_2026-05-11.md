# ORIS vNext Project State — 2026-05-11

## Current vNext state

ORIS vNext has entered Dev Employee Phase 2 scaffold.

The implemented scaffold is intentionally limited to the native Dev Employee baseline:

- Task Kernel scaffold
- Worker Registry
- DevTask schema
- Execution Ledger contract
- CodexExecutor dry-run command contract
- Validation Pipeline contract
- GitHub-oriented summary log convention

## Current primary runtime chain

The current intended runtime chain is:

```text
OpenClaw access/channel layer
  -> ORIS Native Task Kernel
  -> Worker Registry / Dev Employee profile
  -> Execution Ledger
  -> CodexExecutor dry-run contract
  -> Validation Pipeline
  -> GitHub docs/log handoff
```

OpenClaw remains the access layer. It must not own ORIS business logic.

## Current authoritative files

- `docs/ORIS_VNEXT_ARCHITECTURE_2026-05-11.md`
- `docs/UPDATED_DEV_EMPLOYEE_PROMPT_2026-05-11.md`
- `docs/DECISIONS/2026-05-11_runtime_simplification_policy.md`
- `config/dev_employee_runtime.json`
- `docs/DEV_EMPLOYEE_PHASE2_SCAFFOLD.md`
- `logs/dev_employee/20260511/phase2_scaffold.summary.md`

## Current validation status

Local validation completed before commit:

```bash
python3 -m compileall -q /mnt/data/oris_scaffold/oris_vnext /mnt/data/oris_scaffold/scripts/dev_employee_smoke.py
cd /mnt/data/oris_scaffold && python3 scripts/dev_employee_smoke.py --dry-run
```

Observed result:

```json
{"ok": true, "worker_profile": "dev_employee", "model_role": "coding_planning", "codex_dry_run": true}
```

## Known limits

- Real Codex execution remains disabled by default.
- No channel handler has been rewired yet.
- No long-running task queue has been added in this step.
- Existing Insight / Feishu / provider orchestration runtime is not replaced.

## Next implementation order

1. Add repo bootstrap reader that verifies required docs before planning.
2. Add approval-gated real Codex execution mode.
3. Add validation report writer under `logs/dev_employee/YYYYMMDD/` only for decision-useful summaries.
4. Add GitHub log summarizer / handoff updater.
5. Then wire OpenClaw channel handlers to enqueue/handoff into Task Kernel instead of executing long tasks directly.
