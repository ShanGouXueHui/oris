# ORIS Dev Employee Current State — 2026-06-20

## 1. Current task

Task id:

`commercial-openclaw-typed-write-actions-20260620`

Status:

`readonly_p0_completed_latency_baseline_v1_persisted_typed_write_actions_design_pending`

Current step:

`new_chat_audit_current_main_then_reconcile_and_implement_offline_typed_write_action_foundation`

The predecessor task `commercial-openclaw-readonly-tool-enable-20260618` is complete.

## 2. Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS Plugin / Agent Harness
  -> ORIS authorization, task governance, queue and evidence
  -> Codex real code execution
  -> product repository commit and tests
  -> ORIS evidence returned through OpenClaw
```

Fixed decisions:

- `https://control.orisfy.com` is the commercial primary entry;
- `/` uses native OpenClaw UI and sessions;
- custom ORIS Web Console remains restricted administration, diagnostics and rollback only;
- no broad prompt-keyword task creation;
- ORIS integrates through stable typed tools/actions/plugins;
- product code stays in product repositories;
- `main` is the only mainstream branch;
- ZenMux remains excluded;
- production host `8.136.28.6` is out of scope without a separate task.

## 3. Read-only P0 completion

Authoritative evidence commit:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

Checks:

- total: 26;
- pass: 26;
- fail: 0;
- not checked: 0.

Accepted ORIS business tools:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

Typed hooks:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

Verified:

- effective surface contained all three approved Plugin-owned tools;
- model tool-call capability passed;
- ORIS Agent Harness routing passed;
- Free Mesh protocol version 2 preserved tool calls;
- three native natural-language turns passed;
- one persisted native session passed;
- telemetry schema, content safety and permissions passed;
- only authorized ORIS and native support tools were used;
- queue unchanged;
- product repository unchanged;
- source and listener invariants passed;
- no write tool added;
- no product task submitted;
- no OpenClaw reinstall or upgrade.

## 4. Retained runtime state

Plugin:

- id: `oris-dev-employee`;
- version: `0.1.0`.

Policy mode:

`profile-authority-preserved+created-profile-also-allow+skill-unrestricted`

Routing Skill:

- name: `oris-readonly-status`;
- installed: yes;
- Agent: `main`;
- runtime-visible: yes.

Rollback:

- count: 0;
- status: not required;
- reason: the validated read-only policy was retained.

Current write state:

- typed write actions registered: no;
- typed write actions enabled: no;
- generic `exec` tool enabled: no;
- generic file-write tool enabled: no;
- real product write acceptance authorized: no.

## 5. Native Skill support authority

The only approved ORIS business tools remain the three read-only tools above.

Native `read` is permitted only as bounded Skill hydration support:

- maximum one call;
- before the first ORIS business-tool call;
- must succeed;
- not an ORIS business tool;
- not a new effective tool.

Excessive, failed, late, overlapping, write-capable or undeclared support tools remain rejected.

## 6. Initial privacy-safe latency baseline v1

Source evidence:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Model duration:

- samples: 8;
- minimum: 2,661 ms;
- P50: 5,478 ms;
- maximum: 49,734 ms.

Agent total duration:

- samples: 3;
- minimum: 8,538 ms;
- P50: 9,029 ms;
- maximum: 69,134 ms.

Tool duration:

- `oris_queue_status`: 13 ms;
- `oris_task_status`: 42 ms;
- `oris_latest_task_status`: 13–41 ms, P50 27 ms;
- Skill hydration `read`: 92 ms.

Interpretation:

- ORIS tool execution is millisecond-scale;
- model and Agent orchestration dominate observed latency;
- TTFT is unavailable from the approved typed hooks;
- this is an initial observed baseline, not a commercial SLO or SLA;
- more accepted samples are required before alert thresholds or packaging decisions.

## 7. Environment

Development/control/execution:

- host: `43.106.55.255`;
- user: `admin`;
- ORIS path: `/home/admin/projects/oris`.

Production:

- host: `8.136.28.6`;
- user: `deploy`;
- do not touch.

Runtime:

- OpenClaw: `2026.5.19 (a185ca2)`;
- Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`;
- Free Mesh API: `oris-free-mesh-api.service`, loopback `8789`;
- enqueue/status: `127.0.0.1:18891`;
- intake: `127.0.0.1:18892`;
- Web Console: `127.0.0.1:18893`;
- Codex CLI: real code executor.

Product repository:

- GitHub: `ShanGouXueHui/oris-final-acceptance-api`;
- local: `/home/admin/projects/oris-final-acceptance-api`;
- baseline: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

Research database:

- database: `oris_insight`;
- schema: `insight`;
- role: research/insight only;
- must remain separate from Dev Employee task truth.

Provider/model identifiers are runtime facts and must not be hardcoded.

## 8. Engineering and interaction contract

- Chinese, professional, direct and structured communication;
- do not ask the user to decide routine engineering details;
- write long scripts, patches and documents directly to GitHub;
- use one short pull-and-run command only when host execution is required;
- no long heredocs;
- detailed logs under `logs/dev_employee/` and read from GitHub;
- every user-run script prints exactly one final Summary;
- user-facing Linux scripts do not use `set -e`;
- never expose secrets, raw config, private marker, raw session ids, prompts, conversation content or tool arguments/results;
- inspect before editing;
- remove duplicates and competing authorities before feature work;
- one rule has one authoritative implementation;
- separate config and code;
- split mixed-responsibility modules;
- no shared-code hardcoding of project/path/host/port/branch/provider/model/runtime/version or acceptance special cases;
- build a generic commercial implementation;
- temporary branches/backups and detached evidence worktrees are allowed;
- competing long-lived branches are prohibited;
- do not append to tracked evidence after commit;
- completion requires real tests, commit SHA, remote SHA and GitHub evidence.

## 9. Next commercial phase

Authoritative plan:

`docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md`

Goal:

Design and implement the minimum generic offline foundation for typed write actions with:

- typed schemas;
- identity mapping;
- RBAC;
- project authorization;
- risk tiers;
- immutable prepared operations;
- approval and replay protection;
- idempotency;
- atomic task/queue transaction;
- cancellation and explicit terminal retry;
- privacy-safe audit.

The current phase does not authorize runtime activation or a real product task.

## 10. Required next action

Use a new conversation because the current one is near a practical context limit.

The new conversation must:

1. read the durable context in the order defined by `CONTEXT_INDEX_ADDENDUM_2026-06-20.md`;
2. summarize P0 completion, current runtime and remaining work;
3. run a fresh code-first audit on current `main` before source edits or runtime access;
4. inspect existing authorization, task, queue, idempotency, Plugin and Agent Harness authorities;
5. reconcile the phase plan with existing code instead of adding duplicate implementations;
6. implement only the minimum generic offline foundation;
7. keep write actions unregistered and runtime-disabled;
8. publish tests and durable evidence through GitHub.

## 11. Remaining commercialization work

1. typed write actions with approval, RBAC, project authorization, idempotency and audit;
2. generic project onboarding and capability discovery;
3. controlled Admin Provider/Model/Policy management;
4. monitoring, alerts and SLOs;
5. privacy/retention controls;
6. backup/restore, upgrade rollback and disaster recovery;
7. multi-tenant identity and isolation;
8. quota and metering;
9. commercial packaging;
10. production validation under a separate explicit task.
