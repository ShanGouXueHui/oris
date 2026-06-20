# Dev Employee Typed Write Actions Commercial Phase Plan — 2026-06-20

## 1. Purpose

This plan governs the phase after successful native read-only P0.

The goal is to add generic, typed and auditable write-action foundations without exposing arbitrary shell access, broad prompt-triggered task creation or an uncontrolled product mutation path.

This document authorizes design and offline implementation work only. It does not authorize runtime activation of write actions or submission of a real product task.

## 2. Preconditions already satisfied

- native OpenClaw is the commercial primary UI;
- three ORIS read-only tools are enabled and accepted;
- typed lifecycle telemetry is privacy-safe;
- effective tool materialization is proven;
- model tool-call capability and ORIS routing are proven;
- queue and product invariants are proven;
- initial latency baseline v1 is persisted;
- write tools remain absent.

Evidence:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

## 3. Non-goals

The phase must not:

- expose `exec`, shell, generic file write or arbitrary command tools to the model;
- accept executable commands from public user input;
- use broad prompt keyword matching to create tasks;
- hardcode one project, path, host, branch, provider or model;
- place product implementation in the ORIS repository;
- activate production-host changes;
- silently treat conversation history as task truth;
- bypass approval for a risk-bearing action;
- enable write actions before a separate controlled runtime gate is documented and passed.

## 4. Required architecture

```text
natural-language user goal
  -> native OpenClaw typed action selection
  -> Agent Harness schema and risk classification
  -> identity and project authorization
  -> immutable prepared operation
  -> approval decision when required
  -> idempotency reservation
  -> ORIS lifecycle transaction
  -> Codex executor adapter when applicable
  -> product repository validation and delivery
  -> audit/evidence result returned through OpenClaw
```

## 5. Authority boundaries

### 5.1 OpenClaw

Owns:

- user conversation and session;
- typed action invocation;
- model execution;
- native approval interaction where supported.

Does not own:

- canonical task state;
- project authorization truth;
- queue mutation logic;
- product repository mutation logic.

### 5.2 Agent Harness

Owns:

- typed input/output schemas;
- intent-to-action routing;
- risk classification request;
- structured validation;
- conversion between OpenClaw action calls and ORIS domain requests.

Does not own:

- durable task state;
- approval truth;
- project membership;
- queue files or leases.

### 5.3 ORIS

Owns:

- actor identity mapping;
- roles and permissions;
- project authorization;
- operation preparation and immutable intent hashes;
- approval requirements and approval records;
- idempotency;
- task creation, queue transaction and lifecycle;
- cancellation and retry semantics;
- audit events and evidence.

### 5.4 Codex executor

Owns:

- real coding execution within an authorized product repository;
- tests and repair;
- product commit and controlled push;
- structured execution result.

It must not determine user authorization or approval policy.

## 6. Proposed typed action surface

Names are provisional until repository inspection confirms existing action naming authority.

### 6.1 Preparation action

`oris_prepare_goal`

Purpose:

- validate actor, project and requested goal;
- resolve project capability and repository boundary;
- classify risk;
- produce an immutable prepared operation;
- state required approvals;
- perform no queue or product mutation.

Input concepts:

- project identifier;
- natural-language goal;
- requested task type;
- optional constraints;
- client request/idempotency candidate.

Output concepts:

- operation id;
- intent hash;
- normalized project/task summary;
- risk tier;
- required approval mode;
- expiry;
- validation errors;
- no secrets or product content.

### 6.2 Commit/submit action

`oris_submit_goal`

Purpose:

- consume a valid prepared operation;
- verify approval and idempotency;
- create exactly one ORIS task and queue transaction;
- return canonical task identity and state.

Required fields:

- operation id;
- intent hash;
- idempotency key;
- approval reference when required.

Must reject:

- expired or altered operation;
- actor/project mismatch;
- missing or invalid approval;
- duplicate committed operation;
- duplicate idempotency key with different intent;
- unauthorized project/task type;
- dirty or invalid target repository where policy prohibits it.

### 6.3 Cancel action

`oris_cancel_task`

Purpose:

- request cancellation of an authorized active task;
- preserve task and attempt history;
- be idempotent when already cancelling/cancelled;
- never delete evidence.

### 6.4 Explicit retry action

`oris_retry_task`

Purpose:

- retry a retryable terminal task only;
- create a new attempt identity;
- preserve original task and failure evidence;
- require explicit authorization and approval based on risk tier;
- prevent accidental duplicate commits or queue claims.

### 6.5 Approval action or approval adapter

The design must first inspect whether installed OpenClaw provides a stable native approval contract suitable for this version.

If it does, implement an adapter to that contract.

If it does not, keep approval as an ORIS domain interface and do not invent an insecure prompt-only confirmation mechanism.

No approval action may be activated until identity binding and replay protection are verified.

## 7. Risk tiers

### R0 — read-only

Examples:

- queue status;
- task status;
- latest task status;
- project capability discovery.

No mutation. Existing P0 tools remain unchanged.

### R1 — reversible control-plane mutation

Examples:

- prepare operation;
- submit a task before executor claim;
- cancel a queued task.

Requires authenticated actor, project authorization, idempotency and audit. Approval policy may be configurable by project and action.

### R2 — product repository mutation

Examples:

- Codex edits;
- commits;
- controlled push;
- explicit retry after a failed product attempt.

Requires explicit approval, repository preflight, allowed-path policy, executor identity, tests, evidence and rollback/recovery semantics.

### R3 — infrastructure, secrets or production

Examples:

- production host changes;
- secret rotation;
- public network exposure;
- provider credential mutation;
- destructive data operations.

Not authorized by the generic typed write-action phase. Requires a separate explicit task and stronger approval policy.

## 8. Identity and RBAC contract

The implementation must define stable interfaces for:

- actor id;
- tenant id or future tenant boundary;
- OpenClaw session/channel identity mapping;
- role assignments;
- project membership;
- action permission;
- approval permission;
- executor/service identity.

Minimum roles are provisional and must be configuration-backed:

- viewer: R0 only;
- operator: selected R1 actions on authorized projects;
- developer: approved R2 development tasks on authorized projects;
- approver: approve configured risk tiers;
- administrator: policy management, not automatic product mutation.

One actor must not self-approve when project policy requires separation of duties.

## 9. Project authorization

Every mutating action must resolve the project through `orchestration/project_registry.json` or its future authoritative successor.

The resolved contract must include:

- project id;
- repository identity and local path;
- allowed branch policy;
- allowed task types;
- allowed writable paths;
- forbidden paths;
- executor policy;
- required tests;
- approval policy;
- deployment/production restrictions.

No shared module may special-case `oris-final-acceptance-api`.

## 10. Idempotency and transaction rules

Every mutating request requires an idempotency key scoped to actor, project and action.

Rules:

- same key + same intent returns the existing result;
- same key + different intent is rejected;
- prepared operation has an immutable hash and expiry;
- commit consumes the operation exactly once;
- queue insertion and task-state creation form one logical transaction;
- retry creates a new attempt id, not a duplicate task mutation;
- cancel is safely repeatable;
- evidence publication must not create duplicate product commits.

The filesystem-backed current state must use explicit locking/atomic replacement. A future database ledger may replace it only through a documented migration.

## 11. Approval contract

Approval records must bind:

- approver identity;
- actor identity;
- project;
- action;
- operation id;
- intent hash;
- risk tier;
- timestamp and expiry;
- approval policy version;
- one-time/replay status.

Approval must fail closed when:

- identity cannot be resolved;
- operation changed;
- approval expired;
- policy version is incompatible;
- approver lacks authority;
- separation-of-duties rule is violated;
- approval has already been consumed where one-time use is required.

Conversation text alone is not an approval record.

## 12. Audit and privacy

Audit events must record bounded metadata only:

- event type;
- task/operation/attempt ids;
- actor and approver pseudonymous or bounded identifiers;
- project id;
- action and risk tier;
- policy version;
- decision and reason code;
- timestamps and durations;
- product and evidence commit SHAs where applicable.

Must not record:

- prompts or conversation content;
- model hidden reasoning;
- tool arguments/results unless an explicitly sanitized schema requires bounded fields;
- tokens, passwords, keys, cookies, headers or raw auth state;
- raw OpenClaw session identifiers;
- private marker or raw config content;
- product source diffs in control-plane audit events.

## 13. State machine requirements

At minimum, prepared operations and tasks must distinguish:

Prepared operation:

- `prepared`;
- `approval_required`;
- `approved`;
- `rejected`;
- `expired`;
- `consumed`.

Task lifecycle:

- `queued`;
- `claimed`;
- `running`;
- `cancellation_requested`;
- `cancelled`;
- `completed`;
- `failed_retryable`;
- `failed_terminal`.

Never use one boolean for failed versus not checked or approval absent versus rejected.

## 14. Layering and module boundaries

Preferred modules:

- action schemas;
- identity adapter;
- RBAC/project authorization policy;
- risk classifier;
- prepared-operation store;
- approval authority/adapter;
- idempotency authority;
- task transaction service;
- cancellation/retry service;
- audit event publisher;
- OpenClaw Plugin/Agent Harness adapter;
- CLI/runtime entrypoint.

Do not combine all responsibilities in one script or module.

Each rule must have one authoritative implementation.

## 15. Configuration separation

Version-controlled non-secret configuration should define:

- action schemas/versions;
- risk tiers;
- role/action mapping;
- project approval policy references;
- operation expiry limits;
- idempotency retention;
- supported OpenClaw compatibility behavior;
- evidence schema versions.

Secrets and credentials remain local-only.

Runtime identities, provider/model choices and service endpoints must be discovered or configured, never hardcoded into generic shared code.

## 16. Testing gates

Before any runtime activation:

1. complete code-first audit with all findings zero;
2. schema validation tests;
3. RBAC allow/deny matrix tests;
4. project authorization tests;
5. risk-tier tests;
6. approval replay/expiry/separation tests;
7. idempotency same-intent/different-intent tests;
8. atomic task/queue transaction tests;
9. cancel/retry state-machine tests;
10. concurrent duplicate-submission tests;
11. privacy scanner tests;
12. regression tests for all previously observed runtime failures;
13. compile/static/full unit tests;
14. no OpenClaw runtime access in the contract-only test stage.

## 17. Controlled runtime activation gate

Write actions must remain absent until a separate document and script prove:

- exact source revision passed code audit;
- read-only P0 remains healthy;
- effective surface contains only intended new actions;
- no generic write/exec tool is added;
- identity and project authorization resolve correctly;
- approval flow is real and replay-safe;
- a non-product sandbox fixture can verify transaction behavior;
- queue/product/source/listener invariants are defined;
- rollback restores the exact prior read-only policy and Plugin state;
- evidence is privacy-safe and published from a detached worktree.

A real product task must not be the first activation test.

## 18. Next-chat execution boundary

The next conversation should:

1. read the new durable context in the mandatory order;
2. summarize current P0 completion and open work;
3. run a fresh code-first audit on current `main` before source edits;
4. inspect existing task, authorization, queue, idempotency, Plugin and Agent Harness authorities;
5. reconcile this plan with existing implementations instead of creating duplicates;
6. implement only the minimum generic offline foundation;
7. keep write actions unregistered and runtime-disabled;
8. publish tests and durable design updates through GitHub;
9. stop before runtime activation unless a separate controlled gate has been created and audited.
