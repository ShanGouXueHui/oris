# ORIS Dev Employee Current State — 2026-06-16

## Executive status

ORIS Dev Employee has moved beyond local prototype status.
The current system has a real public Web control entry, durable task intake/status, a supervised bridge, Codex CLI execution, GitHub evidence, and an independent acceptance product repository.

The end-to-end public flow is structurally working through task enqueue, but the latest real task failed before code execution because Codex authentication could not refresh its token.

Current phase:

> Commercialization hardening of the Dev Employee control plane and execution reliability.

## Current architecture actually in use

### Public access

- Official domain base: `orisfy.com`
- Dev Employee public entry: `https://control.orisfy.com`
- Nginx terminates HTTPS and enforces Basic Auth.
- Only the exact Web Console task endpoint permits public POST.
- The intake service is never proxied directly to the Internet.

### Local services

- Web Console: `127.0.0.1:18893`
- Intake/status API: `127.0.0.1:18892`
- Supervised bridge: systemd user service
- OpenClaw gateway historical baseline: `127.0.0.1:18789`

Service names:

- `oris-dev-employee-web-console.service`
- `oris-dev-employee-intake.service`
- `oris-dev-employee-bridge.service`

### Security controls

Persistent public submission is enabled with all of these controls:

1. HTTPS
2. outer Basic Auth
3. inner `X-ORIS-Console-Token`
4. project allowlist
5. body/method restrictions in Nginx
6. sanitized submit audit logging
7. loopback-only intake and Web Console backends
8. no token/header values committed to GitHub

Current public project allowlist:

- `oris-final-acceptance-api`

The Console Token was rotated after accidental chat exposure. The replacement value remains local and must never be pasted into chat or committed.

## Verified milestones

### Platform and execution

- Codex CLI real host execution was previously verified.
- GitHub SSH push and remote SHA verification were previously verified.
- The supervised bridge claims queued tasks and produces task evidence.
- Strict result schema and skill-resolution evidence enforcement exist.
- Failure evidence persistence, triage, repair planning, and acceptance harnesses exist.
- GitHub evidence commit indexing exists.

### Intake and status

- Loopback intake/status API exists and is systemd-supervised.
- Public Web Console proxies through the local Web Console, not directly to intake.
- Project filtering/allowlisting works.
- Public Web submit can remain persistently enabled under the security controls above.
- Submit attempts are audited without storing secret values.

### Public Web Console UX

The following Web UI defects were fixed and validated:

- empty project dropdown after entering a token;
- project reload not triggered after token changes;
- Python string escaping breaking rendered JavaScript;
- JavaScript syntax now passes a real syntax check;
- `/api/projects` returns `oris-final-acceptance-api` under valid token auth.

Relevant platform commits include:

- `8bc8584` — persistent public Web submit enabled
- `2bb5727` — token-aware project dropdown
- `11bec4c` — JavaScript escaping fixed and verified

### Public reverse proxy

Verified behavior:

- unauthenticated access returns 401;
- authenticated `/health` returns 200;
- direct intake is not exposed;
- exact `/api/goals` POST is permitted only through the authenticated Web Console path;
- other write methods remain blocked;
- Nginx duplicate `server_name` conflict was removed;
- htpasswd permissions were corrected for the Nginx worker.

## Product repositories

### ORIS platform

- GitHub: `ShanGouXueHui/oris`
- local path: `/home/admin/projects/oris`
- branch policy: `main` is the only mainstream branch
- role: platform orchestration, control, execution policy, registry, diagnostics, and evidence

### Final acceptance product

- GitHub: `ShanGouXueHui/oris-final-acceptance-api`
- local path: `/home/admin/projects/oris-final-acceptance-api`
- stack: FastAPI + pytest + httpx
- role: independent acceptance/test product

Product code must remain in the product repository. It must not be written into the ORIS platform repository.

## Latest real public task

Task id:

`goal-oris-final-acceptance-api-20260616-031022`

Requested objective:

- add `GET /readonly-e2e`;
- return exactly `{"readonly_e2e": true}`;
- add pytest coverage;
- run tests;
- commit and push.

Observed flow:

1. public Web UI accepted the request;
2. project allowlist resolved correctly;
3. intake returned HTTP 201;
4. task was queued;
5. bridge claimed the task;
6. Codex process started;
7. Codex authentication failed before implementation;
8. failure evidence and triage were persisted to GitHub.

Final task state:

- status: `codex_failed`
- bridge service: active
- product commit: none
- product remote SHA: none
- ORIS failure evidence commit: `ea2089c5344c67e016601de8993ef365591daa06`
- diagnostic log commit: `6fbc0ba1636ca01865b9565e68fdf6689ed6cae5`

## Confirmed root cause

Codex log shows:

- HTTP 401 during token refresh;
- error code `refresh_token_reused`;
- message requiring logout and sign-in again;
- WebSocket connection then failed with 401.

This is an authentication state problem, not a project code, prompt, repository, Nginx, intake, or bridge-availability problem.

## Current blocker

Codex CLI must be reauthenticated and verified in the same execution identity/context used by the systemd bridge.

Do not submit another real development task until all of the following pass:

1. interactive Codex re-login is complete;
2. `codex --version` works;
3. a minimal non-interactive `codex exec` works under user `admin`;
4. the same command works from the bridge service environment;
5. auth preflight is added before a task is claimed or before Codex execution;
6. auth failure is classified as a terminal status immediately;
7. the Web E2E finisher treats `codex_failed` and other failure states as terminal.

## Immediate next plan

### P0 — restore execution

1. inspect current Codex auth files without printing secret content;
2. log out and sign in again as `admin`;
3. verify non-interactive execution with a harmless no-write prompt;
4. verify systemd bridge environment can access the same auth state;
5. add an explicit Codex auth preflight;
6. rerun the original objective using a new task id.

### P1 — harden task lifecycle

- define canonical terminal states;
- stop polling on `codex_failed`, `host_checks_failed`, `blocked`, `failed`, or `error`;
- expose failure category and next action clearly in Web status;
- add retry/requeue as an explicit controlled action, never an implicit infinite loop;
- ensure failed tasks cannot remain visually `queued` in catalog summaries.

### P2 — commercial productization

- registry-driven project onboarding instead of one hardcoded acceptance project;
- role-based access and per-project authorization;
- durable task queue backed by database or transaction-safe store;
- structured audit and retention policy;
- observability dashboards and alerting;
- executor/provider health checks;
- safe cancellation, retry, timeout, and concurrency controls;
- generic deployment/install/upgrade/rollback runbooks;
- remove test-project-specific assumptions from reusable runtime code.

## Operating constraints

- Do not ask the user to choose routine engineering steps.
- Directly update GitHub for long scripts and documents.
- User executes short commands or GitHub-hosted `.sh` scripts.
- Logs are committed to GitHub and inspected there.
- Every operational script must end with `===== SUMMARY =====` and `===== END SUMMARY =====`.
- The user should paste only the SUMMARY block into chat.
- Never print secrets in SUMMARY or GitHub logs.
- Do not use `set -e` in user-facing Linux scripts.
- Keep stable configuration separate from secrets and runtime noise.
