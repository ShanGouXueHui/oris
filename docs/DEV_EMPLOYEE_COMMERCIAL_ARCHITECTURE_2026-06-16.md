# ORIS Dev Employee Commercial Architecture — 2026-06-16

## 1. Product definition

ORIS Dev Employee is an AI software-engineering employee, not a chat assistant and not a shell wrapper.

The commercial product must accept a goal, bind it to an approved project, decide routine engineering steps, execute through a governed coding executor, validate the result, commit and push, and return auditable evidence.

OpenClaw remains an access/channel gateway. It is not the business-logic owner or the source of truth for task state.

## 2. Layered architecture

### L1 — Access and channel layer

Components:

- public Web Console at `control.orisfy.com`;
- OpenClaw Web/channel access;
- future Feishu/QQ/CLI entrypoints.

Responsibilities:

- authenticate the human;
- collect goal, constraints, project, and optional task metadata;
- display task status and evidence;
- never perform long-running coding work in the request handler.

Boundary:

- access handlers only normalize and enqueue requests;
- no direct product repository mutation;
- no direct Codex orchestration logic in UI code.

### L2 — Edge security and policy layer

Current implementation:

- Nginx HTTPS termination;
- Basic Auth;
- method/path restrictions;
- request-size and rate-limit controls;
- reverse proxy to loopback Web Console only.

Commercial target:

- SSO/OIDC or enterprise identity;
- RBAC and per-project authorization;
- CSRF protection where browser sessions replace token headers;
- explicit emergency disable switch;
- immutable audit identity and request correlation id.

### L3 — Task intake and kernel

Current components:

- Web Console API;
- intake/status API;
- project registry;
- queue descriptors;
- task catalog and task-run evidence files.

Responsibilities:

- validate schema;
- bind project and allowed scope;
- generate task id;
- persist normalized objective and constraints;
- assign lifecycle state;
- enqueue exactly once;
- expose status and evidence.

Commercial target:

- transaction-safe persistence;
- idempotency keys;
- concurrency and lease control;
- cancellation and controlled retry;
- canonical state machine;
- database-backed task/event ledger while retaining GitHub delivery evidence.

### L4 — Planning and policy layer

Responsibilities:

- read durable project context;
- choose the smallest safe implementation plan;
- resolve existing ORIS-owned capabilities first;
- apply autonomy doctrine and stop conditions;
- avoid asking humans for routine engineering choices.

Stable policy belongs in versioned docs/config, not in transient prompt prose alone.

### L5 — Execution mesh

Current primary executor:

- Codex CLI under the `admin` host identity.

Additional executor families remain possible:

- controlled shell executor;
- Git executor;
- test executor;
- artifact executor;
- future alternative coding executors.

Rules:

- reasoning and execution are separate;
- executor identity, cwd, writable scope, timeout, model/provider, and auth preflight are explicit;
- product code is written only in the target product repository;
- ORIS platform files are changed only when the task explicitly targets ORIS or evidence must be recorded;
- every execution produces structured logs and a machine-readable result.

### L6 — Validation and delivery

Responsibilities:

- run static/syntax checks;
- run targeted and full tests;
- verify changed-file scope;
- verify Git working tree state;
- commit and push product changes;
- verify remote SHA;
- commit ORIS evidence separately;
- present concise status to the user.

Completion is not inferred from model text. It is proven by command output, repository state, tests, commits, and remote verification.

### L7 — Memory and evidence

Sources of truth:

1. GitHub docs and decisions for project memory;
2. task/event store for operational state;
3. GitHub commits and evidence artifacts for delivery proof;
4. PostgreSQL insight schema for research/evidence workloads;
5. local secret stores for credentials.

Chat history is not an operational database.

### L8 — Evaluation and evolution

Responsibilities:

- classify failures;
- track reliability by stage;
- compare executor/model paths;
- generate repair plans;
- convert repeated successful fixes into reusable code/config/docs;
- prevent test-specific patches from becoming permanent architecture.

## 3. Canonical task lifecycle

Recommended commercial state machine:

- `accepted`
- `validated`
- `queued`
- `claimed`
- `preflight_failed`
- `planning`
- `executing`
- `local_checks_failed`
- `local_checks_passed`
- `committing`
- `pushing`
- `remote_verification_failed`
- `completed`
- `blocked`
- `cancelled`
- `failed`

Current legacy states such as `codex_failed`, `host_checks_failed`, and `bridge_exception` should remain accepted as detailed failure codes, but map to a canonical terminal `failed` or `preflight_failed` state.

Terminal states must stop polling immediately.

## 4. Security boundaries

### Publicly reachable

- Nginx HTTPS endpoint;
- authenticated Web Console routes only.

### Loopback only

- Web Console backend;
- intake/status backend;
- OpenClaw gateway unless explicitly redesigned;
- internal execution/control services.

### Never committed

- Console Token;
- intake token;
- provider tokens;
- Codex auth material;
- Basic Auth password/hash source material beyond the host-managed htpasswd file;
- private keys;
- production credentials;
- `.env` files.

### Scope enforcement

Each project must define:

- repository identity;
- local path;
- default branch;
- allowed paths;
- forbidden paths;
- required checks;
- deployment boundary;
- approval boundary.

## 5. Configuration model

- secrets: local secret store/environment only;
- stable non-sensitive policy: `config/`, `orchestration/`, schemas, and docs;
- generated baselines: committed only when intentionally promoted;
- runtime files: local and ignored by default;
- high-frequency operations policy: database/Admin UI;
- one authoritative source per rule.

## 6. Repository boundaries

### ORIS repository

Owns:

- orchestration;
- intake/status/control APIs;
- executor adapters;
- policy and schemas;
- project registry;
- evaluation;
- evidence indexing;
- operational runbooks.

Does not own:

- unrelated product application code;
- duplicated product modules;
- secrets;
- environment-specific credentials.

### Product repositories

Own:

- product source code;
- product tests;
- product-specific docs/config;
- product release history.

## 7. Commercial generalization requirements

Before onboarding business-critical projects, replace acceptance-specific assumptions with generic mechanisms:

- registry-backed project selection;
- project-specific checks and policies;
- reusable executor contract;
- reusable result schema;
- generic state/event model;
- project-independent Web UI;
- tenant/user/project authorization;
- configurable retry/timeouts/concurrency;
- install, upgrade, backup, rollback, and disaster recovery runbooks;
- service health/metrics/alerts;
- retention and audit policy.

## 8. Current implementation assessment

Working:

- secured public Web entry;
- persistent authenticated submit path;
- project allowlist;
- local intake/status service;
- supervised bridge;
- Codex invocation;
- strict result/evidence contracts;
- failure persistence and triage;
- GitHub evidence model.

Immediate reliability gap:

- Codex auth can expire or enter `refresh_token_reused` state without a preflight gate.

Immediate architecture correction:

- auth/provider/executor health must be validated before a task is claimed for execution;
- authentication failure must be visible as a terminal preflight failure with a precise remediation action.
