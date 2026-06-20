# ORIS / OpenClaw / Codex-backed AI Dev Employee Completion Archive — 2026-06-20

## 1. Purpose and authority

This file completes the durable archive of the long 2026-06-20 commercialization conversation.

It covers:

- the original startup mandate;
- the fixed architecture and product decisions;
- environment, systems, repositories, database and runtime boundaries;
- interaction and engineering rules;
- the complete effective-tool, model/tool, Free Mesh, telemetry and native-Agent acceptance sequence;
- the final read-only P0 result;
- the first privacy-safe latency baseline;
- unfinished work from the original mandate;
- the next commercial phase.

Historical failure evidence remains immutable. This file supersedes mutable status, current-runtime and next-action conclusions in:

- `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md`;
- earlier sections of `memory/dev_employee/CONTEXT_INDEX.md`;
- earlier handoff documents that describe the runtime as tools-denied or the effective surface as unresolved.

The latest authority order is defined by `memory/dev_employee/CONTEXT_INDEX_ADDENDUM_2026-06-20.md`.

## 2. Original startup mandate

The conversation began with a strict continuation request for the existing ORIS / OpenClaw / Codex-backed AI Dev Employee commercialization project.

Non-negotiable instructions were:

- do not redesign from scratch;
- do not depend on chat history as project truth;
- read GitHub durable context before execution;
- preserve the existing repository and architecture;
- perform a complete code-first audit before touching OpenClaw runtime;
- remove duplicate definitions, competing authorities, duplicate function bodies, import cycles, oversized mixed-responsibility modules, hardcoding, legacy execution paths and contract errors;
- do not hide real defects with scanner allowlists;
- keep one authoritative implementation per rule;
- separate policy, runtime adapters, service control, validation, evidence and entrypoints;
- do not access OpenClaw, restart Gateway, run model turns or submit product tasks until the code gate passes;
- use native Gateway RPC `tools.effective` for effective-surface diagnosis;
- preserve exact rollback and final invariants;
- use detached worktrees for evidence publication;
- keep detailed logs in GitHub and return only a compact Summary to chat;
- build a generic commercial platform, not an acceptance-project special case.

The original commercial priority list was:

1. bring code governance findings to zero;
2. resolve effective tool materialization or provider/model tool-call capability;
3. complete native natural-language acceptance for all three read-only ORIS tools;
4. establish real privacy-safe model/tool/Agent latency baselines;
5. after P0, design typed write actions with approval, RBAC, project authorization, idempotency and audit;
6. generic project onboarding and capability discovery;
7. Admin UI Provider, Model and Policy management;
8. monitoring, privacy/retention, backup/restore and disaster recovery;
9. multi-tenant identity, quota, metering and commercial packaging.

## 3. Fixed commercial architecture

The approved commercial chain remains:

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS Plugin / Agent Harness
  -> ORIS authorization, task governance, queue and evidence
  -> Codex real code execution
  -> product repository commit and tests
  -> ORIS evidence returned through OpenClaw
```

### 3.1 UI and session decisions

- Public primary interface: `https://control.orisfy.com`.
- `/` is the native OpenClaw UI.
- Native OpenClaw sessions are the user-facing conversation authority.
- The custom ORIS Web Console is not the primary product UI.
- `/admin` and `/_oris-chat-shell` remain restricted administration, diagnostics and rollback paths only.

### 3.2 Responsibility boundaries

- OpenClaw owns conversation, sessions, model execution and plugin hosting.
- The native ORIS Plugin exposes typed tools/actions and privacy-safe lifecycle telemetry.
- Agent Harness owns tool/action schemas, routing and policy adaptation, not persistent task truth.
- ORIS owns project authorization, task identity, lifecycle, queue, leases, retry/cancel semantics, evidence and audit.
- Codex CLI is the real coding executor.
- Product repositories own product source, tests, documentation and delivery commits.

### 3.3 Irreversible product decisions

- Do not rebuild native conversation features in the custom ORIS Web Console.
- Do not restore broad prompt-keyword task creation.
- Integrate ORIS through stable typed tools/actions/plugins.
- Reuse the existing `openclaw-gateway.service` and `127.0.0.1:18789`.
- Do not reinstall or upgrade OpenClaw as generic troubleshooting.
- Do not reinstall the Plugin as generic troubleshooting.
- Keep ports `18891` and `18892` loopback-only.
- Keep product code, tests and documentation in independent product repositories.
- `main` is the only mainstream branch.
- ZenMux remains excluded unless explicitly reopened.
- Production host `8.136.28.6` remains out of scope without a separate production task.

## 4. Environment and surrounding systems

### 4.1 Development/control/execution host

- host: `43.106.55.255`;
- user: `admin`;
- projects root: `/home/admin/projects`;
- ORIS repository: `/home/admin/projects/oris`;
- GitHub repository: `ShanGouXueHui/oris`;
- mainstream branch: `main`.

### 4.2 Production host

- host: `8.136.28.6`;
- user: `deploy`;
- status: do not touch in the current commercialization phase.

### 4.3 Runtime topology

- public entry: `https://control.orisfy.com`;
- OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`;
- Free Mesh API: `oris-free-mesh-api.service`, loopback port `8789`;
- ORIS enqueue/status: `127.0.0.1:18891`;
- ORIS intake: `127.0.0.1:18892`;
- ORIS Web Console: `127.0.0.1:18893`;
- supervised bridge: `oris-dev-employee-bridge.service`.

### 4.4 Runtime versions and execution identities

- OpenClaw: `2026.5.19 (a185ca2)`;
- Node: `v22.22.2`;
- npm: `10.9.7`;
- Codex CLI: real coding executor.

Provider and model identity, capabilities, quotas, latency and cost remain runtime facts. Shared code must not hardcode them.

The successful read-only acceptance observed bounded identifiers `provider=oris` and `model=free-auto`. These are evidence from one run, not permanent configuration authority.

### 4.5 Repositories

ORIS platform:

- GitHub: `ShanGouXueHui/oris`;
- local: `/home/admin/projects/oris`.

Final acceptance product:

- GitHub: `ShanGouXueHui/oris-final-acceptance-api`;
- local: `/home/admin/projects/oris-final-acceptance-api`;
- verified product/remote baseline: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

The product repository remained unchanged throughout read-only OpenClaw work.

### 4.6 Data and state boundaries

Dev Employee operational truth remains filesystem-backed:

- queue: `orchestration/dev_employee_queue/`;
- intake catalog: `orchestration/dev_employee_intake_catalog/`;
- task runs: `orchestration/task_runs/`;
- promoted evidence: `logs/dev_employee/`;
- durable context: `memory/dev_employee/` and `docs/`;
- project authority: `orchestration/project_registry.json`.

Separate research database:

- PostgreSQL database: `oris_insight`;
- schema: `insight`;
- role: research/insight only;
- security status: `ALREADY_SECURE_AND_VERIFIED`;
- evidence: `bc799a640138a19800270ecab1a656f09d70252a`.

Do not silently move Dev Employee task truth into PostgreSQL. A database-backed task/event ledger requires a separate architecture decision and migration plan.

## 5. Interaction and operating contract

- Communicate in Chinese, professionally, directly and structurally.
- Do not ask the user to decide routine engineering details.
- Perform deterministic engineering steps automatically when available.
- Write long scripts, patches and documents directly to GitHub.
- When host execution is unavoidable, provide one short pull-and-run command only.
- Do not provide long heredocs; the terminal channel can truncate them.
- Write detailed logs under `logs/dev_employee/`.
- Read detailed evidence directly from GitHub rather than asking the user to paste it.
- Every user-run script must end with exactly one `===== SUMMARY =====` block.
- The user returns only that Summary.
- User-facing Linux scripts must not use `set -e`.
- Do not expose tokens, passwords, private keys, raw config, raw session identifiers, conversation content, tool arguments/results or private marker content.
- Do not append to a tracked evidence log after its commit.
- Use detached worktrees for evidence publication when appropriate.
- Completion requires real deliverables, tests, local SHA, remote SHA and GitHub evidence.

## 6. Engineering standard

The authoritative standards remain:

- `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`;
- `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`;
- `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`.

Mandatory rules include:

- inspect before editing;
- code-first audit before runtime mutation;
- remove duplicate functions, classes, variables, parsers, validators, policies, helpers, entrypoints and module bindings;
- one rule has one authoritative implementation;
- no competing authority;
- no duplicate function bodies;
- no import cycles;
- split oversized modules by responsibility;
- separate config from code;
- no project/path/host/port/branch/provider/model/runtime/version or acceptance special-case hardcoding in shared code;
- no legacy execution path remaining active without explicit authority;
- do not suppress true defects through scanner allowlists;
- use schemas at boundaries;
- preserve tri-state PASS/FAIL/NOT_CHECKED semantics;
- keep runtime adapters, policy, service control, validation, evidence and entrypoint orchestration separate;
- use `main` as the only mainstream branch;
- temporary branches, backups and detached worktrees are allowed, but competing long-lived branches are prohibited;
- build for multiple projects, users, task types, executors and future tenants;
- product work lands in product repositories; ORIS evidence lands in ORIS.

## 7. Complete execution chronology

### 7.1 Code-first governance

Multiple code-first audits and fixes were completed during the conversation. Structural defects included duplicate bindings, duplicated helper/authority paths, scanner self-findings and mixed-responsibility modules.

The latest source revision before final runtime acceptance passed the unified audit with:

```text
DUPLICATE_BINDINGS=0
AUTHORITY_VIOLATIONS=0
DUPLICATE_FUNCTION_BODIES=0
IMPORT_CYCLES=0
OVERSIZED_MODULES=0
FORBIDDEN_HARDCODING=0
LEGACY_PATH_FINDINGS=0
CONTRACT_ERROR=
```

The support-tool contract PR audit covered 117 authority-scope files and 98 Python architecture files.

### 7.2 Effective tool surface

Evidence commit:

`57636946573e149028fc5d180db75c3cecb316ba`

Result:

- native Gateway RPC `tools.effective` succeeded;
- all three approved ORIS tools were present;
- all were Plugin-owned;
- write tools were absent;
- queue and product were unchanged;
- exact rollback succeeded.

This resolved optional-tool materialization as not being the blocking issue.

### 7.3 Initial model/tool diagnostics

Evidence `f01e2e8b2b3285e1debce57122fa28ee261084a0` exposed an automatic selftest failure and was not accepted as a runtime capability result.

Evidence `b755ef846ce4dd13b62c3642a8ba62862a494f97` then showed:

- effective surface passed;
- direct tool calls passed;
- no native Agent tool call was observed;
- runtime rolled back safely.

The unresolved boundary moved to provider/model tool-call capability and Agent Harness routing.

### 7.4 Free Mesh protocol correction

An intermediate Free Mesh activation failed with `free_mesh_protocol_v2_not_ready`. Service journal analysis and code correction restored protocol version 2 tool-call preservation.

Evidence commit:

`c415c614ac726906186da1756e3beb7c2de003b2`

Result:

- `MODEL_TOOL_CALL_AND_ORIS_ROUTING_PASS`;
- 26/26 checks passed;
- safe built-in tool call passed;
- ORIS queue tool call passed;
- effective approved tools: 3/3;
- telemetry privacy passed;
- persisted native session passed;
- rollback healthy;
- no product task and no write tool.

This resolved provider/model tool-call capability and ORIS Agent Harness routing.

### 7.5 First complete three-tool acceptance

Evidence commit:

`22ee300081e98d8e2df4c3f4a495c9608db98d2b`

The runtime completed the three-tool path but the acceptance result was rejected because telemetry schema validation incorrectly treated valid `success`/`error` outcome booleans as malformed schema.

The fix separated:

- record schema validity;
- execution outcome validity.

Merge commit:

`e3f9ef451f35fee679c4c040d83dcbe017cec9aa`

Regression coverage required:

- each required ORIS tool has at least one non-failed call;
- failed intermediate attempts may recover;
- failed Agent completion remains terminal;
- invalid boolean types remain schema failures.

### 7.6 Second complete acceptance

Evidence commit:

`59725fd783732464b6aec0f249868e78e30a5da2`

The schema correction passed. All three ORIS tools succeeded and execution outcomes were healthy. The sole rejection was one native `read` tool used by OpenClaw to load the approved routing Skill body.

The correction separated:

- ORIS business-tool authority;
- bounded native Skill-support authority.

The approved ORIS business tools remained unchanged:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

The native support contract permits only:

- tool: `read`;
- maximum calls: 1;
- must succeed;
- must occur before the first ORIS business-tool call;
- not an ORIS business capability;
- not a new effective tool.

It rejects excessive, failed, late, overlapping, write-capable or undeclared support tools.

Merge commit:

`bf084296d60de6941303f227cde8f952a6117147`

### 7.7 Final native read-only acceptance

Evidence commit:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Evidence files:

- `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260620T213307Z.json`;
- `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260620T213307Z.log`.

Final result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

Checks:

- total: 26;
- pass: 26;
- fail: 0;
- not checked: 0.

Verified capabilities and invariants:

- source code governance passed;
- automatic selftests passed;
- authoritative readiness passed;
- initial tools-denied baseline passed;
- Gateway and public routes healthy;
- internal listeners loopback-only;
- queue baseline captured with zero active tasks;
- product baseline and clean worktree verified;
- ORIS source baseline verified;
- Free Mesh protocol version 2 and tool calling passed;
- activation candidate dry-run passed;
- exact candidate snapshot passed;
- private backup passed;
- routing Skill installed and runtime-visible to Agent `main`;
- minimal read-only policy enabled;
- Plugin runtime tools and hooks verified;
- direct tool calls passed;
- three native natural-language turns passed;
- telemetry privacy, schema and permissions passed;
- queue remained unchanged;
- product repository remained unchanged;
- final runtime/routes/listeners/source invariants passed;
- private marker recorded;
- write tools absent;
- no product task submitted;
- no OpenClaw reinstall or upgrade;
- rollback count 0 because the validated policy was retained.

Current retained policy mode:

`profile-authority-preserved+created-profile-also-allow+skill-unrestricted`

Routing Skill:

- name: `oris-readonly-status`;
- installed: yes;
- visible to Agent `main`: yes.

The read-only P0 task is complete.

## 8. Initial privacy-safe latency baseline v1

The final accepted run produced real typed-hook latency data without prompts, conversation content, tool arguments/results, secrets or raw session identifiers.

### 8.1 Model duration

- sample count: 8;
- minimum: 2,661 ms;
- P50: 5,478 ms;
- maximum: 49,734 ms.

### 8.2 Agent total duration

- sample count: 3;
- minimum: 8,538 ms;
- P50: 9,029 ms;
- maximum: 69,134 ms.

### 8.3 ORIS tool duration

`oris_queue_status`:

- count: 1;
- minimum/P50/maximum: 13 ms.

`oris_task_status`:

- count: 1;
- minimum/P50/maximum: 42 ms.

`oris_latest_task_status`:

- count: 2;
- minimum: 13 ms;
- P50: 27 ms;
- maximum: 41 ms.

### 8.4 Native Skill support duration

`read`:

- count: 1;
- minimum/P50/maximum: 92 ms.

### 8.5 Interpretation

- ORIS tool execution is currently millisecond-scale.
- Most observed user-path latency is model and Agent orchestration time, not ORIS read-only tool execution.
- One recoverable duplicate attempt occurred for `oris_latest_task_status`; the final execution outcome remained healthy.
- TTFT is not available because the approved typed hooks do not expose a first-token timestamp.
- This is an initial observed baseline, not a commercial SLO or SLA.
- A statistically useful baseline requires more accepted samples across time, provider/model runtime facts and load conditions.

## 9. Original mandate completion status

Completed:

1. current code-governance findings brought to zero for the accepted source revision;
2. effective tool materialization resolved;
3. provider/model tool-call capability and Agent Harness routing demonstrated;
4. all three read-only tools accepted through native natural language;
5. non-zero authorized-only `after_tool_call` telemetry accepted;
6. read-only P0 retained in runtime with no rollback;
7. privacy-safe initial model/tool/Agent latency baseline established;
8. queue/product/source/listener/write-tool invariants verified.

Still open:

1. typed write actions with approval, RBAC, project authorization, idempotency and audit;
2. generic project onboarding and capability discovery;
3. controlled Admin UI for Provider, Model and Policy management;
4. monitoring, operational alerts and SLOs;
5. privacy and retention policy enforcement;
6. backup, restore, upgrade rollback and disaster recovery;
7. multi-tenant identity and isolation;
8. quota and metering;
9. commercial packaging;
10. production deployment and production-host validation under a separate explicit task.

## 10. Next commercial phase

The next task is not to enable a generic write tool.

The next phase is to design and implement a controlled typed write-action foundation.

Mandatory sequence:

1. read the latest durable context;
2. perform a fresh code-first audit on current `main` before source changes;
3. preserve the validated read-only policy and tools;
4. define typed action schemas and risk tiers;
5. define identity, RBAC and project authorization boundaries;
6. define prepare/approve/commit semantics;
7. define idempotency and duplicate-prevention contracts;
8. define queue transaction and audit-event semantics;
9. define cancellation and explicit terminal retry behavior;
10. add offline tests and static governance;
11. do not expose or activate write actions until a separate controlled runtime gate passes;
12. do not submit a real product task as part of contract-only design.

Authoritative next-phase plan:

`docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md`

## 11. Current final state

- read-only P0: complete;
- three native ORIS tools: enabled and accepted;
- Routing Skill: installed and visible;
- telemetry: accepted and privacy-safe;
- initial latency baseline: persisted;
- write tools/actions: not enabled;
- active product task: none;
- product repository: unchanged at verified baseline;
- Gateway: healthy;
- queue: unchanged and no active task at acceptance;
- production: untouched;
- next phase: controlled typed write actions design and implementation foundation.
