# ORIS Dev Employee Context Index Addendum — 2026-06-20

This addendum supersedes the mutable task status and immediate-next-action sections in the earlier `memory/dev_employee/CONTEXT_INDEX.md`. Historical references remain valid.

## Current mandatory read order

1. `memory/dev_employee/CURRENT_STATE_2026-06-20.md`
2. `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md`
3. `memory/dev_employee/ENVIRONMENT_AND_WORKING_CONTEXT_2026-06-20.md`
4. `memory/dev_employee/current_task.json`
5. `memory/dev_employee/current_task.md`
6. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-20.md`
7. `docs/DEV_EMPLOYEE_CODE_FIRST_CONTINUATION_GATE_2026-06-20.md`
8. `docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`
9. evidence commit `d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`
10. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_CORRECTION_2026-06-20.md`
11. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
12. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
13. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
14. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
15. `orchestration/project_registry.json`

## Current task

- task id: `commercial-openclaw-readonly-tool-enable-20260618`;
- status: `handoff_archived_pending_new_chat_code_first_continuation`;
- current step: `new_chat_audit_current_main_then_diagnose_effective_tool_surface`.

## Current next action

Start a new conversation with `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-20.md`.

The new conversation must first audit and fix current `main`. It may run the native effective-tool-surface diagnostic only after the exact audited commit returns `CODE_AUDIT_PASS` with all tracked findings at zero.

The full enablement entrypoint remains prohibited.
