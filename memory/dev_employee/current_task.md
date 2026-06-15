# Current AI Dev Employee Task

Status: blocked

Task id: `goal-oris-final-acceptance-api-20260616-031022`

Target project: `oris-final-acceptance-api`

Target repository: `ShanGouXueHui/oris-final-acceptance-api`

Target local path: `/home/admin/projects/oris-final-acceptance-api`

## Current objective

Complete the first real project task submitted through the persistent public Web Console and prove the full chain:

`public Web UI → Web Console auth/allowlist → intake → queue → bridge → Codex → product tests → product commit/push → ORIS evidence`.

The requested product change is a minimal `GET /readonly-e2e` endpoint with pytest coverage.

## What succeeded

- `https://control.orisfy.com` is operational behind HTTPS and Basic Auth.
- Persistent public submit is enabled for the exact `/api/goals` path.
- Console Token authentication works.
- Project allowlist returns `oris-final-acceptance-api`.
- The project dropdown and reload behavior were fixed.
- Rendered browser JavaScript now passes syntax validation.
- The public task was accepted with HTTP 201.
- The task was persisted, queued, and claimed by the bridge.
- Failure evidence and automated triage were committed to GitHub.
- Web Console, intake, and bridge services remain active.

## Current failure

The Codex process started but failed before changing product code.

Failure classification:

- runtime status: `codex_failed`
- failure code: `codex_authentication`
- return code: `1`
- provider response: HTTP 401

No product commit or remote product SHA was produced.

## Evidence

- ORIS failure evidence commit: `ea2089c5344c67e016601de8993ef365591daa06`
- diagnostic commit: `6fbc0ba1636ca01865b9565e68fdf6689ed6cae5`
- Codex log: `logs/dev_employee/goal-oris-final-acceptance-api-20260616-031022.codex.log`
- diagnostic log: `logs/dev_employee/codex_failed_diagnostics/goal-oris-final-acceptance-api-20260616-031022-20260616031848.log`

## Immediate next action

1. Reauthenticate Codex CLI as Linux user `admin`.
2. Verify a harmless non-interactive Codex execution.
3. Verify the same authentication context is available to `oris-dev-employee-bridge.service`.
4. Add a Codex authentication preflight before real execution.
5. Classify auth failure as terminal and fail fast.
6. Update polling/finisher logic so `codex_failed` and all other terminal failures stop immediately.
7. Resubmit the same product objective with a new task id.
8. Verify product commit, product remote SHA, tests, and ORIS evidence.

## Do not do yet

- Do not submit another real project task before auth preflight passes.
- Do not weaken Basic Auth, Console Token, or project allowlist.
- Do not expose intake port 18892 publicly.
- Do not place product code in the ORIS repository.
- Do not paste tokens or authentication material into chat or GitHub.

## Authoritative context

Read:

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-16.md`
3. `docs/DEV_EMPLOYEE_COMMERCIAL_ARCHITECTURE_2026-06-16.md`
4. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_2026-06-16.md`
5. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`

## Operating rule

Do not ask the human for routine engineering decisions. Inspect GitHub evidence, choose the smallest safe action, implement it through GitHub-hosted scripts, and stop only at an explicit authentication, secret, safety, paid-resource, or destructive-production boundary.
