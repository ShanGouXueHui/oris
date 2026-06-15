# ORIS Dev Employee Engineering Standard — 2026-06-16

## 1. Scope

This standard applies to ORIS platform code, Dev Employee control/execution components, project adapters, operational scripts, and product changes executed by ORIS.

The goal is a reusable commercial system, not a collection of one-off acceptance scripts.

## 2. Core principles

### 2.1 Layered and decoupled

Keep these responsibilities separate:

- access/channel;
- authentication and edge policy;
- task intake/kernel;
- planning/policy;
- execution adapters;
- validation/delivery;
- evidence/memory;
- evaluation/evolution.

A Web handler must not contain repository mutation or Codex process-management logic.
An executor must not own UI policy.
A product adapter must not redefine global auth, queue, or evidence behavior.

### 2.2 Configuration separation

Use this hierarchy:

1. secrets in local secret stores/environment;
2. stable non-sensitive configuration in version-controlled config/schema files;
3. intentionally promoted generated baselines in GitHub;
4. runtime noise in ignored local storage;
5. high-frequency operational policy in database/Admin UI.

A rule has one authoritative source. Do not duplicate the same rule in Python, shell, Nginx, and docs without an explicit derivation mechanism.

### 2.3 Repository separation

- ORIS repository contains platform orchestration and evidence.
- Product repositories contain product code and product tests.
- Do not copy product code into ORIS for convenience.
- Cross-repository operations must record both product SHA and ORIS evidence SHA.

### 2.4 One mainstream branch

- `main` is the mainstream branch.
- Backups may be files, tags, commits, or short-lived branches when justified.
- Do not create competing long-lived branches for ordinary development.
- Completed work must merge/land on `main` unless the user explicitly requests another workflow.

### 2.5 Generic commercial implementation

Do not hardcode acceptance-project behavior into shared modules.

Acceptance-specific values must enter through:

- project registry;
- task payload;
- project policy/config;
- test fixtures.

Shared code must support multiple projects, users, task types, and executors without copy-paste forks.

## 3. Code organization

Preferred pattern:

- pure domain/state logic separated from I/O;
- adapters around Nginx, systemd, Git, Codex, GitHub, database, and filesystem;
- schemas at boundaries;
- explicit dependency direction;
- small modules with one reason to change;
- reusable libraries rather than repeated patch scripts.

Operational patch scripts are acceptable for controlled migration, but a successful patch must later be consolidated into the authoritative installer/config generator or product module.

## 4. Task and state model

### 4.1 Explicit schemas

All task descriptors, results, evidence indexes, and project entries must have machine-readable schemas or validation logic.

Reject invalid data early with precise errors.

### 4.2 Canonical states

Use a defined state machine and distinguish:

- current state;
- detailed failure code;
- terminal/non-terminal classification;
- retryability;
- required human action.

Never poll indefinitely because a new failure state was omitted from a shell `if` statement.

### 4.3 Idempotency

Task submission and execution must support:

- unique task ids;
- duplicate detection;
- safe retry with new attempt identity;
- no accidental duplicate commits;
- no duplicate queue claims.

## 5. Executor standard

Every coding executor invocation must define:

- executable identity and version;
- user identity;
- working directory;
- target repository/path;
- allowed writable paths;
- sandbox/approval mode;
- model/provider;
- timeout;
- auth preflight;
- result path;
- log path;
- expected success schema.

Before claiming or executing a real task, preflight:

- executor exists;
- authentication is usable;
- target repository exists and matches registry;
- Git remote matches expected repo;
- target branch is correct;
- working tree policy is satisfied;
- required interpreter/toolchain exists;
- required disk/network resources are available.

## 6. Security standard

- least privilege;
- loopback-only internal services by default;
- HTTPS for public entry;
- outer identity plus inner service authorization until replaced by a stronger unified identity system;
- explicit project authorization;
- secrets redacted at source, not after logging;
- request body limits;
- rate limits;
- audit events with request/task correlation ids;
- emergency disable switch;
- no arbitrary shell command input from public users;
- no unreviewed third-party skill installation or execution.

## 7. Testing standard

### 7.1 Minimum checks

For Python/FastAPI product changes:

- syntax/compile check;
- targeted test for the changed behavior;
- full `pytest -q`;
- stricter warning check where relevant;
- changed-file/scope validation.

### 7.2 Platform changes

Platform changes require tests at the correct boundary:

- unit tests for state/policy logic;
- integration tests for API/queue/bridge contracts;
- offline Nginx/systemd config validation;
- end-to-end test for public submit through final GitHub evidence;
- regression test for each previously observed production-like failure.

### 7.3 Exact evidence

Store exact command, return code, and output path.
Do not summarize a failed command as passed.
Do not claim push success without comparing local and remote SHA.

## 8. Git and evidence standard

A successful product task records:

- task id;
- product repository and path;
- changed files;
- test outputs;
- product commit SHA;
- product remote SHA;
- ORIS evidence files;
- ORIS evidence commit SHA;
- final clean/known-dirty status.

A failed task records:

- failure stage;
- detailed failure code;
- return code;
- relevant sanitized log path;
- retryable/non-retryable decision;
- next recommended action;
- whether the product repository changed.

## 9. Operational script standard

User-facing scripts must:

- live in GitHub;
- be executable from project root;
- avoid `set -e`;
- use explicit failure boundaries;
- be safe to rerun or detect prior application;
- back up host configuration before destructive replacement;
- validate syntax before restart/reload;
- never echo secrets into logs;
- write detailed logs under a stable path;
- commit only useful evidence;
- print one final SUMMARY block.

Required ending:

```text
===== SUMMARY =====
RESULT=PASS|REVIEW|FAILED|DIAGNOSED
...
SEND_TO_CHAT=THIS_SUMMARY_ONLY
===== END SUMMARY =====
```

## 10. Documentation standard

- latest dated state documents are authoritative;
- historical documents remain historical and are marked superseded;
- architecture decisions go to durable docs/decision records;
- configuration changes update docs and handoff;
- new conversations read GitHub first;
- do not make chat history the only location of a critical decision.

## 11. Commercial readiness gates

Before enabling business-critical repositories:

1. reliable executor auth preflight;
2. canonical terminal-state handling;
3. transaction-safe queue/claim model;
4. cancellation, timeout, retry, and concurrency controls;
5. project-level RBAC;
6. audit retention and privacy policy;
7. monitoring and alerts;
8. generic project onboarding;
9. upgrade/rollback/disaster-recovery runbooks;
10. security review and dependency/vulnerability process;
11. stable API/versioning contract;
12. measurable E2E success-rate target.

## 12. Current corrective actions

The latest `refresh_token_reused` failure creates these mandatory engineering tasks:

- add Codex auth preflight before execution;
- classify auth failure before product mutation;
- expose `codex_authentication` as a structured failure code;
- stop status polling immediately on terminal failure;
- provide a safe reauthentication runbook;
- verify the bridge service uses the same auth home/context as interactive `admin`;
- add a regression test that simulates executor-auth failure.
