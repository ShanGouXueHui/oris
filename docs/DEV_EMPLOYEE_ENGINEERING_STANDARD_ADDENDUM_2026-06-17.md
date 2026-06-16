# ORIS Dev Employee Engineering Standard Addendum — 2026-06-17

This addendum supplements `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md` and overrides conflicting implementation assumptions.

## 1. Product and UI boundary

The native OpenClaw UI is the approved primary conversation interface.

Do not continue rebuilding standard conversation-product capabilities in the custom ORIS Web Console, including:

- conversation history;
- new conversation;
- session switching;
- clearing/archive/delete;
- native prompt behavior;
- channel/session lifecycle.

The custom shell may remain only as a restricted diagnostic or rollback surface during migration.

Agent Harness is a backend tool/policy adapter, not the main UI.

## 2. Prompt and tool integration

Normal user development goals must be expressed in natural language without ORIS-specific syntax.

Do not create tasks through broad substring/keyword matching inside arbitrary prompt text.

OpenClaw-to-ORIS integration must use explicit tool/action schemas for:

- list authorized projects;
- create goal;
- get current status and evidence;
- cancel an active task;
- explicitly retry a terminal task;
- request confirmation for genuinely risky actions.

Control commands may use deterministic handling only when they are exact, short commands. A word embedded in a long engineering request must not trigger a control action.

Negative safety constraints such as `不要修改密钥` are constraints, not requests to operate on secrets.

## 3. Layered dependency direction

Required dependency direction:

```text
native OpenClaw UI/channel
  -> tool/action adapter
  -> Agent Harness policy/schema
  -> ORIS intake and lifecycle kernel
  -> executor adapter
  -> Codex
  -> product repository
```

Forbidden coupling:

- UI code mutating queue files or product repositories;
- Harness owning task state;
- OpenClaw conversation history acting as the task database;
- executor code owning UI policy;
- product adapters redefining global auth or lifecycle rules;
- ORIS platform code copied into product repositories;
- product code copied into ORIS.

## 4. Configuration separation

Use one authoritative source per rule:

- secrets: local secret store/environment only;
- stable non-sensitive config: version-controlled config/schema/registry;
- runtime operational state: local ignored store or future database;
- promoted evidence: GitHub;
- UI display text: presentation layer, derived from canonical state;
- project policy: project registry or project-specific policy config.

Do not duplicate one policy independently in Prompt, Python, Shell and Nginx. Generate or derive lower-level rules from the authoritative source where practical.

## 5. Branch and repository policy

- `main` is the only mainstream branch.
- Backups are allowed as private archives, files, commits, tags or short-lived migration branches.
- Do not create competing long-lived branches.
- Completed product work lands in the product repository.
- ORIS evidence lands separately in the ORIS repository.
- Completion requires product commit SHA, product remote SHA and ORIS evidence SHA.

## 6. Generic commercial implementation

Shared modules must not hardcode `oris-final-acceptance-api` or any other acceptance project.

Project-specific values must come from:

- `orchestration/project_registry.json`;
- the task payload;
- project policy/config;
- test fixtures.

Build for multiple projects, users, tenants, task types and executors.

## 7. Completion contract

A task is not complete because:

- the model says it is complete;
- the UI status says `completed`;
- some tests pass;
- a commit exists.

Completion requires verification of every explicit requested deliverable:

1. changed-file scope matches the request;
2. syntax/static checks pass;
3. targeted checks pass;
4. full required tests pass;
5. documentation/config requested by the user is changed;
6. product commit exists;
7. product remote SHA matches;
8. product worktree is clean or has an explicitly accepted known state;
9. ORIS evidence is committed and remote;
10. canonical task state is terminal `completed`.

The `/capabilities` browser task demonstrated why this matters: code and tests were committed, but the requested README update was omitted. That task is partially delivered, not fully accepted.

## 8. Executor preflight

Before a real task is claimed or executed, verify:

- Codex executable and version;
- authentication in the exact bridge identity/context;
- target repository path and remote;
- target branch;
- local/remote baseline SHA;
- worktree policy;
- allowed and forbidden paths;
- interpreter/toolchain availability;
- timeout, sandbox and result schema;
- disk/network prerequisites.

Auth failure must be terminal before product mutation.

## 9. Nginx and host migration rules

For every public-route migration:

- inspect with `nginx -T`;
- detect duplicate/conflicting server names;
- patch only the effective server block;
- back up the exact file privately;
- validate generated config offline;
- run `nginx -t`;
- reload only after validation;
- test public and loopback behavior;
- preserve unrelated route/method restrictions;
- roll back automatically on failure;
- never expose intake directly.

Native OpenClaw migration must preserve WebSocket, token and device-pairing behavior.

## 10. Test environment fidelity

Tests must run with the same module resolution and relevant environment contract as the service.

Rules:

- set `PYTHONPATH` explicitly when modules under `scripts/` are imported as top-level runtime modules;
- do not assume `/usr/bin/python3` contains pytest;
- use the project virtual environment or standard-library `unittest` when applicable;
- record exact command and return code;
- add regression tests for every production-like failure.

## 11. Git and log drift control

Do not append to a tracked log after committing it.

When the main worktree contains an intentional patch:

- archive it privately with checksums before synchronization;
- use a detached worktree for evidence commits;
- ensure evidence generation does not alter the primary worktree;
- synchronize local `HEAD`, index and worktree deliberately;
- preserve only intended source patches;
- reject unexpected source drift;
- treat allowlisted diagnostic log drift separately from source drift.

Raw chat sessions and raw Harness traces are runtime state and must remain ignored.

## 12. User-facing script standard

User-run scripts must:

- be committed to GitHub;
- be fetched and executed with a short command;
- avoid `set -e`;
- use explicit failure handling;
- be repeatable or detect prior application;
- back up before mutation;
- validate before restart/reload;
- roll back on failure;
- avoid secrets in logs and output;
- write verbose details to files, not the terminal;
- print exactly one final `===== SUMMARY =====` block.

Long inline heredocs should not be given to the user because their terminal execution channel can truncate them.

## 13. Commercial priorities after native UI migration

1. stable OpenClaw tool/action contract;
2. identity mapping and per-project RBAC;
3. audit retention and privacy policy;
4. rate limiting and abuse controls;
5. monitoring, alerts and SLOs;
6. backup/restore and upgrade/rollback automation;
7. generic project onboarding;
8. database-backed task/event ledger and distributed-safe leases.
