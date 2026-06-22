# Current State: ORIS Autonomous Runtime v2 Handoff

Date: 2026-06-22
Repo: `ShanGouXueHui/oris`
Primary issue: `https://github.com/ShanGouXueHui/oris/issues/15`
Authority doc: `docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md`

## Why this handoff exists

The current conversation is long enough that continuing to rely on chat context is risky. This document persists the full operational context, decisions, incomplete tasks, environment constraints, and next-chat startup prompt into GitHub so a new chat can continue without relying on transient context.

## Strategic decision

ORIS is not a manually watched script collection. ORIS must become a persistent autonomous AI development employee runtime.

The target capability is:

- user submits a high-level product/platform goal from OpenClaw Web;
- ORIS decomposes the work into modules;
- ORIS generates compact context packs;
- ORIS invokes Codex CLI and validated skills;
- ORIS develops, tests, repairs, commits, pushes, and records evidence;
- ORIS continues module-by-module without humans making routine engineering decisions;
- browser/terminal disconnects must not stop execution;
- every module writes GitHub evidence;
- final products are deployment-smoke-tested and commercially accepted.

## Completed work in this conversation

### 1. ORIS final acceptance context was read

The conversation started from the accepted ORIS / OpenClaw / Codex-backed Dev Employee state. Key accepted chain:

```text
OpenClaw/ORIS task intake -> queue/status API -> supervised bridge -> Codex CLI real execution -> product repository verification -> product commit SHA capture -> ORIS evidence files generation -> ORIS evidence commit and push -> status API terminal=true -> verifier acceptance=true
```

The accepted final demo task was `demo-openclaw-web-task-board-20260622015615` and proved that Codex-backed product repo execution and ORIS evidence capture can work when driven carefully.

### 2. Insight product kickoff began

The desired product was a commercial insight employee, similar to a high-end consulting analyst:

- company profile;
- market structure;
- competitor landscape;
- financial quality;
- product/capability comparison;
- strategy signals;
- risk/scenario view;
- evidence-backed executive brief.

Target product repo:

```text
ShanGouXueHui/oris-commercial-insight-employee
```

Target local path:

```text
/home/admin/projects/oris-commercial-insight-employee
```

Project key:

```text
oris-commercial-insight-employee
```

### 3. Historical insight assets were audited

Historical ORIS insight assets were found under `scripts/lib/`:

- `scripts/lib/insight_db.py`
- `scripts/lib/insight_db_config.py`
- `scripts/lib/insight_db_records.py`
- `scripts/lib/insight_db_schema.py`
- `scripts/lib/insight_db_utils.py`

Judgment:

- reuse concepts: evidence item, metric observation, analysis run, source snapshot, company profile, citation/evidence model, deterministic reporting principles;
- refactor before reuse: DB config, secret resolver, PostgreSQL coupling, monolithic facade;
- defer for product Phase 0: DB write, external source ingestion, citations DB persistence, artifact generation, Feishu/Qbot delivery.

### 4. Product repo was created and initialized

Remote repo was initially missing, then user created it. The assistant initialized remote README and `.gitignore` through GitHub connector.

Initial commits:

- README initialization: `ee8ecb6e0154626d908bb2a14e6748e6bd62f58a`
- `.gitignore` creation: `216ec91b327ecbccd0e7ed6aaded450fa00c8de8`

### 5. Module 0 recovered and committed local implementation

OpenClaw/ORIS Web was used to recover the local product work and commit it.

Module 0 result commit:

```text
7d1d604b92b21f1213f990140b3345b4be2163ca
```

Commit message stated:

- added `app/`, `tests/`, `docs/`, `requirements.txt`;
- verified Python compilation;
- tests passed: 5 passed;
- fixed strict warning mode issue;
- synced to GitHub.

Remote verification confirmed:

- `app/main.py` contains FastAPI app, Pydantic models, health endpoints, executive brief endpoint, and deterministic workflow;
- `tests/test_health.py` covers `/healthz` and `/healthz/details`;
- `tests/test_executive_brief.py` covers executive brief response structure;
- `requirements.txt` contains FastAPI/Pydantic/pytest/httpx dependencies.

### 6. Module 1 started but was not verified complete

Module 1 objective was modularization only:

- keep public API behavior unchanged;
- split `app/main.py` into models, routes, workflows;
- add evidence files:
  - `docs/testing/MODULE_1_TEST_PLAN.md`
  - `reports/testing/module_1_test_result.json`
  - `reports/testing/latest_test_result.json`
- commit and push only after all tests pass.

OpenClaw appeared to stall or context grew long. GitHub search did not find Module 1 commit at the time of last verification. Module 1 should be considered incomplete unless a later commit exists.

### 7. The strategic pivot was made

Because the interactive Insight Product run required too much human prompting, the project pivoted:

Do not continue expanding the current interactive insight product as the main goal.

Instead:

1. Stop or abandon the stuck interactive run.
2. Upgrade ORIS itself to Autonomous Dev Employee Runtime v2.
3. After Runtime v2 exists, use it to rebuild or replace the insight capability as the end-to-end acceptance demo.

### 8. Runtime v2 acceptance project was created

GitHub issue created:

```text
https://github.com/ShanGouXueHui/oris/issues/15
```

Authority doc committed:

```text
docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md
```

Commit:

```text
01f828ba1c20995dd1c69a4540a55c92ea93087f
```

## Current failure / blocker

The assistant provided SSH commands for `admin@43.106.55.255`, but execution failed before connecting:

```text
admin@43.106.55.255: Permission denied (publickey).
```

This means the user environment running the command lacks the SSH private key or authorized identity for the `admin` account on `43.106.55.255`.

No remote process was killed and no Runtime v2 task was enqueued through SSH.

This failure is operational access, not an ORIS code failure.

## Environment and host roles

Known environment from project memory and repository documents:

- Singapore / development host: `43.106.55.255`, user `admin`, expected ORIS path `/home/admin/projects/oris`, Codex CLI installed/authenticated historically.
- Hangzhou / production host: `8.136.28.6`, user `deploy`, should not be touched unless explicitly authorized for production deployment.
- ORIS repo: `ShanGouXueHui/oris`.
- Product insight repo: `ShanGouXueHui/oris-commercial-insight-employee`.
- Accepted final acceptance product repo: `ShanGouXueHui/oris-final-acceptance-api`.

The user sometimes refers to the Singapore machine as the machine to execute on. Prior durable project context classifies it as development host. Preserve that distinction unless the user explicitly reclassifies it.

Ports / services from existing context:

- OpenClaw gateway: `127.0.0.1:18789` / public `https://control.orisfy.com`
- ORIS queue/status/intake: `127.0.0.1:18892` for intake API in recent scripts
- custom web console historically around `18893`

## Interaction rules and user preferences

- Use Chinese for coordination.
- Style: professional, direct, structured, data/evidence-driven.
- Prefer GitHub as durable memory and evidence source.
- Do not rely on long chat context.
- Prefer direct GitHub writes over asking user to paste long logs.
- When asking user to execute commands, provide copy-paste-ready commands.
- Do not use `set -e` in shell commands; it can unexpectedly exit the shell in this environment.
- Keep commands staged and observable.
- Logs should go to `/tmp`, `logs/`, or `run/`; only tail key lines.
- If a task is dynamic or long-running, write state/evidence to GitHub and ORIS files.

## Engineering standards to preserve

- ORIS repo is platform/orchestration/governance/evidence runtime, not business product code.
- Business products must live in separate product repositories.
- Layered architecture: API / orchestration / runtime / adapters / domain / tests.
- Configuration separated from code.
- One active mainstream branch: `main`.
- Backups/branches are allowed, but avoid parallel unreconciled mainlines.
- Preserve compatibility facades where existing entrypoints import old names.
- Generic, commercial reusable implementation; avoid one-off demos.
- Test-first or test-backed changes.
- Every module must have test plan, result JSON, execution report, and commit SHA.
- Evidence-first: no module is complete without GitHub evidence.
- No hardcoded secrets, private tokens, private env files, credentials, or production keys.
- Downloaded skills must be quarantined and validated before execution.
- Human escalation only for credentials, paid resources, unsafe production operations, destructive DB operations, legal/compliance/security risk, or repeated bounded failures.

## Runtime v2 acceptance modules

A. Architecture and State Machine Design
B. Persistent Queue and Run State Schema
C. Detached Worker Service
D. Context Pack Generator
E. GitHub Evidence Writer
F. Module Planner and Bounded Agent Loop
G. Skill Resolver Integration
H. Deployment Smoke Verifier
I. End-to-End Demo Using Insight Product

## Immediate next plan

1. Start a new chat with the handoff prompt in `memory/dev_employee/NEXT_CHAT_START_PROMPT_2026-06-22_AUTONOMOUS_RUNTIME_V2.md`.
2. Read the authoritative files listed there from GitHub.
3. Verify whether Module 1 in `oris-commercial-insight-employee` ever completed after the last check.
4. Do not continue product feature expansion.
5. Solve the operational access issue:
   - either user runs commands from a machine with SSH key access to `admin@43.106.55.255`;
   - or user executes commands directly inside the server session;
   - or use ORIS/OpenClaw Web if write actions are enabled.
6. Enqueue or implement Runtime v2 Module A as the next platform module.
7. Use GitHub as verifier: inspect commits, test plans, result JSON, reports, and ORIS evidence.

## Explicitly unfinished work

- Kill stuck OpenClaw/Codex process on `43.106.55.255`: not completed due SSH publickey denial.
- Runtime v2 worker implementation: not started.
- Runtime v2 Module A: not started.
- Runtime v2 Modules B-I: not started.
- Insight product rebuild by upgraded Runtime v2: not started.
- Module 1 modularization of current insight product: started/instructed but not verified complete.
- ORIS registry update for `oris-commercial-insight-employee`: likely not completed unless later commit exists.

## Verification rule for next chat

Do not trust UI text alone. Verify via GitHub:

- commits exist;
- expected files exist;
- tests and reports exist;
- evidence JSON has structured verdict;
- ORIS evidence references product/platform commit SHA.
