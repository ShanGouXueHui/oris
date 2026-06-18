# ORIS Dev Employee Commercialization Priorities — 2026-06-18

## Current position

The native OpenClaw UI migration is complete. The native `oris-dev-employee` mixed plugin is installed and enabled with three runtime-verified read-only tools and three runtime-verified telemetry hooks. The tools remain denied pending controlled enablement.

The project is no longer blocked on UI migration, plugin SDK compatibility, plugin installation or product README completion.

## P0 — Controlled read-only tool enablement

Goal: make ORIS status capabilities usable from native OpenClaw without exposing mutation actions.

Required gates:

- read-only readiness evidence before mutation;
- exact effective tool-policy discovery;
- reversible config change;
- only three approved tools exposed;
- no submit/cancel/retry tool;
- direct tool invocation tests;
- native browser natural-language smoke test;
- no queue mutation;
- no product task submission;
- authentication and restricted routes unchanged;
- automatic return to tools-denied state on failure.

Completion evidence must record config backup, policy diff, runtime inventory, tool outputs after sanitization, queue fingerprint, product baseline, local/remote evidence SHA and final rollback status.

## P0 — Latency and privacy observability

Goal: determine whether the response delay observed in the native UI is normal and identify where time is spent.

Measure separately:

- public HTTP/UI transport overhead;
- time to first model token where available;
- model call duration;
- tool call duration;
- total agent-turn duration;
- ORIS loopback API duration;
- Gateway/plugin overhead.

Use the installed hooks:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

Telemetry acceptance must confirm:

- local file mode and bounded rotation;
- no prompt, message, response, tool argument/result, header or credential content;
- only bounded metadata and hashed identifiers;
- sufficient correlation to distinguish model latency, tool latency and total turn latency.

Do not claim a latency baseline until real samples exist.

## P1 — Explicit write actions

Only after P0 passes, design write-side actions as separate, explicit contracts. Do not extend the read-only tools into hidden mutation behavior.

Minimum controls:

- explicit target project and repository;
- project registry authorization;
- authenticated user/operator identity;
- approval before mutation;
- idempotency key and duplicate detection;
- canonical task state machine;
- cancellation, timeout and retry semantics;
- queue capacity and concurrency policy;
- Codex auth/executor preflight;
- product scope validation;
- exact product commit and remote SHA verification;
- ORIS evidence commit;
- compensating rollback where delivery has not completed.

Initial write actions should be narrow and typed, for example submit a reviewed development task or request task cancellation. Broad prompt keyword matching remains prohibited.

## P1 — Native conversation integration

The native OpenClaw session is the user-facing control surface. ORIS should return structured task identity and progress without replacing standard conversation semantics.

Required behavior:

- task id and target project visible;
- current canonical state visible;
- progress and evidence links available;
- terminal state stops polling;
- failures distinguish retryable, non-retryable and human-action-required;
- follow-up conversation can reference the existing task without duplicate submission.

## P2 — Generic project onboarding

Convert project onboarding into a schema-driven commercial capability:

- repository identity and branch;
- local path;
- writable and forbidden scopes;
- toolchain/test contract;
- deployment policy;
- secrets required by name, never value;
- execution timeout and resource policy;
- approval level;
- completion and rollback contract.

No acceptance-project-specific branching is allowed in shared modules.

## P2 — Admin and configuration governance

Routine operational policy must move from ad hoc file editing into a controlled Admin surface backed by a single authoritative configuration model.

Priority controls:

- provider/model availability and routing;
- project allowlists and execution scopes;
- tool enablement and approval policy;
- queue capacity and concurrency;
- timeouts and retry limits;
- plugin health and telemetry state;
- emergency disable/kill switch;
- evidence retention and privacy settings.

Secrets remain in local secret stores or environment references, not the Admin database as plaintext.

## P2 — Reliability and operations

Commercial rollout requires:

- service health and dependency monitoring;
- queue age, lease, heartbeat and deadline alerts;
- model/provider failure and quota alerts;
- Codex authentication and execution preflight alerts;
- evidence push/remote-SHA mismatch alerts;
- plugin/Gateway rollback runbooks;
- backup restore tests;
- controlled OpenClaw/plugin upgrade policy;
- disaster recovery objectives.

## P3 — Multi-tenant commercial controls

After the execution chain is reliable:

- tenant/user identity and RBAC;
- per-user and per-project quotas;
- cost/token accounting;
- audit and retention policy;
- data isolation;
- billing/metering boundaries;
- service-level objectives;
- commercial packaging and support tiers.

## Decision rule

Do not move to a later priority while an earlier priority lacks evidence. A UI success message is not completion; completion requires real tests, runtime state, commit SHA, remote SHA and durable ORIS evidence.
