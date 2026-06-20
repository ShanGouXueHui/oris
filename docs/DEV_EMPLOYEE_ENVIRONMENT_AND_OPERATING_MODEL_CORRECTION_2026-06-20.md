# Environment and Operating Model Correction — 2026-06-20

## Scope

This correction supersedes only the mutable current-action guidance in section 13 of:

`docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`

All stable environment, topology, ownership, database, privacy, interaction, engineering and branch rules in that addendum remain authoritative.

## Correct current state

The historical dual-stage Gateway-health diagnostic is no longer the current minimum action.

The project has since completed:

- source-governance remediation;
- single-scope `profile + alsoAllow` policy correction;
- installed OpenClaw native dry-run validation;
- controlled activation with successful Gateway, Skill, plugin inventory and direct ORIS tool calls;
- healthy rollback after native Agent turns emitted no tool calls.

Latest activation evidence:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

## Correct next-action authority

Mutable current action is now defined only by:

- `memory/dev_employee/CURRENT_STATE_2026-06-20.md`;
- `memory/dev_employee/current_task.json`;
- `memory/dev_employee/current_task.md`;
- `memory/dev_employee/CONTEXT_INDEX_ADDENDUM_2026-06-20.md`.

The current order is:

1. start a new conversation from the durable handoff;
2. run and fix a fresh code-first audit on current `main`;
3. only after `CODE_AUDIT_PASS`, execute the native effective-tool-surface diagnostic once;
4. read GitHub evidence before selecting a materialization/session-policy or provider/model-capability remediation path.

Do not rerun the full read-only enablement transaction at this stage.
