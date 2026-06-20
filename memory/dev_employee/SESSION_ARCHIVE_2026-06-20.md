# ORIS / OpenClaw / Codex-backed AI Dev Employee Session Archive — 2026-06-20

## 1. Purpose and authority

This archive preserves the full commercial-readiness work completed in the long 2026-06-20 conversation, including the original continuation prompt, all material engineering decisions, execution outcomes, failures, remediations, unresolved work and the required continuation order.

It is a durable handoff document. It does not replace historical evidence commits. When a historical document conflicts with this archive, use the authority order in `memory/dev_employee/CONTEXT_INDEX.md`.

## 2. Original continuation mandate

The session began with the following non-negotiable requirements:

- continue the existing ORIS / OpenClaw / Codex-backed AI Dev Employee commercialization project;
- do not redesign the system from scratch;
- do not rely on chat memory as the source of truth;
- read the GitHub durable context first;
- keep the native OpenClaw UI and native session system as the commercial primary interface;
- retain the custom ORIS Web Console only for restricted `/admin`, rollback and diagnostics;
- use stable typed tools/actions/plugins instead of broad prompt-keyword task creation;
- keep OpenClaw Gateway on the existing `openclaw-gateway.service` and `127.0.0.1:18789`;
- do not reinstall or upgrade OpenClaw during the active task;
- keep enqueue/status `18891` and intake `18892` loopback-only;
- keep product code, tests and product documentation in independent product repositories;
- use `main` as the only mainstream branch;
- exclude ZenMux unless explicitly reopened;
- never print or commit secrets, raw config or private marker content.

The formal commercial chain remains:

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness policy adapter
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

## 3. Fixed product and architecture decisions

### 3.1 UI and session authority

- Public primary UI: `https://control.orisfy.com`.
- `/` serves native OpenClaw.
- Native OpenClaw sessions remain the user-facing session authority.
- Custom ORIS UI is not the commercial primary interface.
- Restricted ORIS UI remains available only for diagnostics, rollback and administration.

### 3.2 Platform responsibilities

- OpenClaw: conversation, sessions, model execution and plugin host.
- Native ORIS plugin: typed read-only tools and privacy-safe lifecycle telemetry.
- Agent Harness: policy, schema, routing and structured-output adapter.
- ORIS: project authorization, task identity, queue, leases, cancellation/retry semantics, evidence and audit.
- Codex CLI: real product implementation, tests, repair, commit and controlled push.
- Product repositories: product source, product tests, product documentation and product delivery commits.

### 3.3 Prohibited shortcuts

- no broad prompt-keyword task creation;
- no OpenClaw reinstall or upgrade as generic troubleshooting;
- no plugin reinstall as generic troubleshooting;
- no product code in the ORIS platform repository;
- no provider/model identity hardcoding in shared code;
- no direct production-host work without a separate explicit production task;
- no write tools until read-only P0 acceptance is complete.

## 4. Environment snapshot

### 4.1 Development/control/execution host

- host: `43.106.55.255`;
- Linux user: `admin`;
- projects root: `/home/admin/projects`;
- ORIS repository: `/home/admin/projects/oris`;
- GitHub: `ShanGouXueHui/oris`;
- mainstream branch: `main`.

### 4.2 Production host

- host: `8.136.28.6`;
- Linux user: `deploy`;
- status: out of scope and must not be touched.

### 4.3 Runtime topology

- OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`;
- ORIS enqueue/status API: `127.0.0.1:18891`;
- ORIS intake API: `127.0.0.1:18892`;
- ORIS Web Console: `127.0.0.1:18893`;
- supervised bridge: `oris-dev-employee-bridge.service`;
- public Nginx entry: `https://control.orisfy.com`.

Ports 18891 and 18892 must remain loopback-only.

### 4.4 Runtime versions

- OpenClaw: `2026.5.19 (a185ca2)`;
- Node: `v22.22.2`;
- npm: `10.9.7`;
- Codex CLI: real code executor.

### 4.5 Repositories

ORIS platform:

- GitHub: `ShanGouXueHui/oris`;
- local: `/home/admin/projects/oris`.

Completed final acceptance product:

- GitHub: `ShanGouXueHui/oris-final-acceptance-api`;
- local: `/home/admin/projects/oris-final-acceptance-api`;
- completed product/remote `main`: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

The product repository remains unchanged during the read-only OpenClaw work.

### 4.6 Data and state boundaries

Dev Employee operational state remains filesystem-backed:

- queue: `orchestration/dev_employee_queue/`;
- intake catalog: `orchestration/dev_employee_intake_catalog/`;
- task runs: `orchestration/task_runs/`;
- promoted evidence: `logs/dev_employee/`;
- durable context: `memory/dev_employee/` and `docs/`;
- project authority: `orchestration/project_registry.json`.

Separate research database:

- PostgreSQL database: `oris_insight`;
- schema: `insight`;
- role: research/insight storage only;
- security result: `ALREADY_SECURE_AND_VERIFIED`;
- evidence: `bc799a640138a19800270ecab1a656f09d70252a`.

Do not couple Dev Employee task state to `oris_insight` without a new architecture decision.

### 4.7 Provider and model rules

- OpenClaw controls the conversation provider/model path.
- Codex CLI controls real coding execution.
- Provider/model identity, capability, quota, latency and cost are runtime facts.
- Shared code must not hardcode a provider or model.
- Compatibility rules belong in one validated configuration authority.
- Privacy-safe evidence may retain bounded provider/model identifiers but not prompts, messages, assistant text, tool arguments/results, headers, cookies, tokens or credentials.
- ZenMux remains excluded.

## 5. Interaction and operating contract

- communicate in Chinese, professionally, directly and structurally;
- do not ask the user to decide routine engineering details;
- write long scripts, patches and documents directly to GitHub;
- when host execution is necessary, provide one short pull-and-run command only;
- do not provide long heredocs because the terminal channel truncates or corrupts them;
- write verbose output under `logs/dev_employee/`;
- read detailed evidence directly from GitHub instead of asking the user to paste long logs;
- every user-run script must print exactly one final `===== SUMMARY =====` block;
- the user should return only that Summary;
- user-facing shell scripts must not use `set -e`;
- evidence must not expose secrets, raw config or private marker content;
- do not append to a tracked evidence log after its commit;
- use detached worktrees for evidence publication when appropriate;
- verify local commit SHA, remote `main` SHA and GitHub evidence before declaring completion.

## 6. Engineering standards and code-first rule

Before modifying any source file:

1. scan the complete target scope for duplicate function, class and variable definitions;
2. scan for duplicate parsers, policies, profile expansion logic, service helpers and execution entrypoints;
3. scan for hardcoded project, path, host, port, branch, provider, model, runtime version and acceptance-project values;
4. identify one authoritative implementation for each rule;
5. separate configuration from code;
6. split files that mix policy, runtime adapters, service control, validation, evidence and entrypoint responsibilities;
7. make the minimum generic commercial change;
8. run syntax, static, target and regression tests;
9. validate against the real installed runtime when relevant;
10. publish sanitized evidence.

`main` is the only mainstream branch. Temporary branches, backups and detached evidence worktrees are allowed, but competing long-lived branches are prohibited.

The user explicitly reaffirmed the priority at the end of this session:

> Fix code-quality problems first, especially duplicate function or variable definitions, then continue functional work.

Therefore the next conversation must not execute the effective-tool-surface runtime diagnostic until a fresh code audit on current `main` passes.

## 7. Installed plugin baseline

Plugin:

- id: `oris-dev-employee`;
- version: `0.1.0`;
- source commit: `8f174b49196aac90b505846200ce260f75355b41`;
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`;
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`;
- installation result: `INSTALLED_TOOLS_DENIED`.

Runtime-verified tools:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

Runtime-verified hooks:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

Readiness:

- `26/26 PASS`;
- evidence: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`.

No write tool is authorized.

## 8. Major execution history

### 8.1 Historical candidate activation and Gateway health failure

Evidence:

`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The previous dual-stage candidate was activated and the existing Gateway failed its health gate. The transaction rolled back to the exact tools-denied baseline and restored Gateway health. Runtime inventory and Agent acceptance were not reached.

### 8.2 Validator discovery failures

Evidence:

- `df9d21839974e4adcc6bde9b62db0fe468b3cc76`;
- `7c01b72a8ae71c2cbf62a0ae4032ab245b09335c`.

The diagnostic initially failed due to source-governance/bootstrap issues, then found no safe candidate-path validator through the originally assumed CLI routes.

### 8.3 Code-governance cleanup

The session identified and corrected structural code issues, including:

- duplicate `urllib` module bindings in `gateway_http.py` and `service_control.py`;
- a static hardcoding scanner self-finding;
- duplicate helper/authority paths removed in earlier refactoring;
- large mixed-responsibility logic split by policy, runtime validation, service control, activation gate and rollback authority.

A static audit passed with all tracked findings at zero. Because additional effective-surface diagnostic files were later added, the next conversation must run the same audit again on the latest `main` before runtime execution.

### 8.4 Dual-scope policy rejection and remediation

Evidence:

`366c8b441e8adff5fa684b2255339ad32832cc31`

The installed OpenClaw native dry-run rejected a candidate containing both non-empty `tools.allow` and non-empty `tools.alsoAllow`.

The policy was corrected to one authorization scope:

```text
tools.profile = coding
tools.allow = absent
tools.alsoAllow = exactly the three approved ORIS tools
tools.deny = approved tools removed
```

A subsequent native dry-run passed:

- evidence: `2eb0e06c4dee75486e3f3859337867d638941901`;
- schema and resolvability: pass;
- active config unchanged;
- Gateway not restarted;
- queue/product unchanged.

### 8.5 First controlled activation and stale-selftest failure

Evidence:

`2c5c33adfd04f2c6a2312465c198aa18ceac41c1`

The candidate, Gateway restart, Skill visibility, plugin runtime and direct ORIS tool calls passed. A stale automatic policy selftest still expected the removed dual-scope behavior and raised `AssertionError` before native Agent acceptance.

The selftests were aligned with the single-scope policy, named failures were added, tests were moved before mutation and blocked stages were changed to `NOT_CHECKED`.

Remediation verification evidence:

`30a32ba761418d0e7bcbb04ac2b4e0a9ac0c8e82`.

### 8.6 Second controlled activation and model-facing tool failure

Evidence:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`.

Passed before failure:

- source governance and automatic selftests;
- private candidate native dry-run;
- exact validated-config-to-backup hash match;
- routing Skill installation and visibility to Agent `main`;
- policy activation;
- Gateway restart and health;
- exact plugin tool/hook inventory;
- direct invocation of all three ORIS tools;
- queue invariance after direct calls.

Three native Agent turns then completed through Gateway in one persisted session:

- all return codes: 0;
- all outputs: structured and present;
- no embedded fallback;
- `model_call_ended=3`;
- `agent_end=3`;
- `after_tool_call=0`;
- approved tools observed: none.

Native Agent acceptance failed because no tool invocation occurred.

Rollback succeeded:

- exact tools-denied config restored;
- routing Skill state restored;
- Gateway restarted and remained healthy;
- rollback failure codes: none;
- no task, product mutation or write tool occurred.

## 9. Current unresolved technical boundary

The following facts are proved:

- direct `/tools/invoke` works;
- plugin inventory contains the three tools;
- the routing Skill is visible;
- policy dry-run is valid;
- Gateway model turns work and sessions persist.

These facts do not prove that the selected Agent/model received the three optional plugin tools in its effective model-facing tool surface.

Two explanations remain:

1. the three tools were absent from the effective Agent/model inventory;
2. the tools were present, but the selected runtime provider/model did not emit tool calls.

A third full enablement attempt is prohibited until this boundary is resolved.

## 10. Prepared effective-tool-surface diagnostic

Authoritative plan:

`docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`

Entrypoint:

`scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh`

The diagnostic is designed to:

- compile and pass source governance and named selftests;
- rebuild and native-dry-run the single-scope candidate;
- temporarily activate only the validated read-only policy;
- call native Gateway RPC `tools.effective` for the persisted Agent session;
- run no model turn;
- invoke no ORIS tool;
- retain only sanitized approved-tool inventory metadata;
- always restore the exact tools-denied config, marker and Skill state;
- verify final Gateway, queue, product and listener invariants;
- publish detached-worktree evidence.

Decision rule:

- approved tools absent: fix effective materialization/session-policy resolution;
- approved tools present: diagnose provider/model tool-call capability and Harness routing without hardcoding provider/model identity;
- RPC unavailable or unsafe: rollback and stop; do not substitute catalog inventory or direct calls.

## 11. Work not completed from the original commercialization mandate

The following items remain open:

1. successful native natural-language acceptance for all three read-only tools;
2. non-zero, approved-only `after_tool_call` telemetry;
3. real privacy-safe model/tool/agent latency baseline after accepted native use;
4. persistent completion state for read-only P0;
5. typed write actions with approval, RBAC, project authorization, idempotency and audit;
6. generic project onboarding and capability discovery;
7. controlled Admin UI for Provider, Model and Policy management;
8. monitoring and operational alerting;
9. privacy/retention controls;
10. backup/restore and disaster recovery;
11. multi-tenant identity and isolation;
12. quota, metering and commercial packaging;
13. production deployment or production-host validation.

None of these may be treated as complete based on direct tool calls alone.

## 12. Required continuation order

The next conversation must follow this order:

1. read the durable context listed in `memory/dev_employee/CONTEXT_INDEX.md`;
2. run a fresh code-first audit on current `main` before any runtime execution;
3. fix every duplicate definition, duplicate binding, competing authority, import cycle, hardcoding, oversized module or contract finding;
4. verify the latest effective-surface diagnostic implementation is layered and has one authority per rule;
5. only after `CODE_AUDIT_PASS`, run the effective-tool-surface diagnostic once;
6. read its GitHub evidence;
7. choose the materialization-remediation path or provider/model-capability path based on native `tools.effective` evidence;
8. do not authorize a third full enablement until the boundary is resolved and a new controlled gate is documented.

## 13. Current commercial priority order

1. code-first audit and correction on current `main`;
2. resolve effective tool materialization versus provider/model tool-call capability;
3. complete native read-only tool and telemetry acceptance;
4. establish privacy-safe real model/tool/agent latency baselines;
5. design typed write actions only after read-only P0 passes;
6. add generic project onboarding and capability discovery;
7. add controlled Admin Provider/Model/Policy management;
8. add monitoring, privacy/retention, backup/restore and disaster recovery;
9. add multi-tenant identity, quota, metering and commercial packaging.
