# Dev Employee Autonomous Execution Policy Addendum — 2026-06-16

This addendum overrides outdated pending-status statements in `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`.

## Current validated baseline

The following are implemented:

- independent final-acceptance product repository;
- loopback intake/status service;
- supervised bridge;
- strict task result and evidence contracts;
- failure persistence and triage;
- secured public Web Console;
- persistent public task submission;
- project allowlist and sanitized audit logging;
- GitHub-backed task evidence.

## Current mandatory policy changes

1. Executor readiness must be checked before product mutation.
2. Executor authentication failure is a terminal preflight/execution failure.
3. Pollers must stop on every terminal failure state.
4. Retry must be explicit and bounded, with a new attempt identity.
5. Product completion requires local commit SHA, remote SHA, checks, and ORIS evidence.
6. Public access must continue through the secured Web Console; the intake service remains internal.
7. Operational scripts must be stored in GitHub and end with a non-secret `===== SUMMARY =====` block.
8. `main` remains the only mainstream branch.
9. Product code stays in the product repository; ORIS stays platform-only.
10. Shared modules must be generic and registry-driven, not hardcoded for the acceptance project.

## Current blocker

Task `goal-oris-final-acceptance-api-20260616-031022` reached the bridge and launched the coding executor, but executor authentication failed before product changes.

The immediate next action is to restore and verify the executor login in the same runtime identity used by the bridge, add readiness preflight, and rerun with a new task id.

## Authoritative companion documents

- `memory/dev_employee/CONTEXT_INDEX.md`
- `memory/dev_employee/CURRENT_STATE_2026-06-16.md`
- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-16.md`
- `docs/DEV_EMPLOYEE_COMMERCIAL_ARCHITECTURE_2026-06-16.md`
- `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_2026-06-16.md`
- `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
