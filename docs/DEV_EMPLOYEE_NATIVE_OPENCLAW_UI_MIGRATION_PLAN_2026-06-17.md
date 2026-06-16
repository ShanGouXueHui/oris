# ORIS Dev Employee Native OpenClaw UI Migration Plan — 2026-06-17

## 1. Objective

Replace the custom ORIS Web Console v5 as the primary public conversation UI with the existing native OpenClaw Gateway UI, without reinstalling OpenClaw and without weakening ORIS task governance.

The migration is complete only when a normal user can use native conversation history and submit an unrestricted natural-language development goal that is executed through ORIS and Codex with complete evidence.

## 2. Non-goals

This migration does not:

- redesign the queue kernel;
- replace intake v2 or bridge v3;
- move product code into ORIS;
- expose intake publicly;
- reinstall or upgrade OpenClaw;
- create another custom conversation shell;
- make chat history the task database;
- touch the Hangzhou production host.

## 3. Target topology

```text
Internet
  -> Nginx / HTTPS / outer identity
     -> /                native OpenClaw Gateway UI :18789
     -> /admin           restricted ORIS engineering console :18893
     -> /_oris_rollback  restricted custom ORIS shell :18893

native OpenClaw
  -> ORIS tool/action adapter
     -> Agent Harness policy/schema
        -> intake v2 :18892
           -> queue kernel
              -> bridge v3
                 -> Codex
```

The exact rollback route name may be changed during implementation, but it must be non-default, restricted and documented.

## 4. Phase 0 — freeze and record

Before discovery or mutation:

- confirm no queued/running task;
- confirm product repositories are clean and local/remote SHA are known;
- record service states;
- record current effective Nginx config source;
- privately archive custom chat session runtime data;
- do not delete task/evidence history;
- do not submit a product task.

## 5. Phase 1 — read-only OpenClaw discovery

Create one GitHub-hosted read-only script that records sanitized facts only.

Required discovery:

### Service/process

- systemd unit path and active state;
- executable and arguments without secret values;
- process user and environment-key names only;
- listener ownership for port 18789.

### HTTP/UI

- root response status and content type;
- static asset paths;
- SPA fallback behavior;
- health/status endpoints if present;
- response headers relevant to reverse proxying;
- base-path assumptions.

### WebSocket

- WebSocket endpoint path;
- required upgrade headers;
- origin/host expectations;
- timeout behavior;
- whether a path prefix is supported.

### Authentication

- auth mode and required header/cookie names only;
- token/device pairing state and UI flow;
- no secret values in logs;
- interaction with Nginx Basic Auth.

### Session/history capabilities

Verify from installed runtime/config/UI assets where possible:

- new conversation;
- conversation list/history;
- conversation switching;
- clear/archive/delete;
- session storage location/type;
- multi-device/session behavior;
- whether these capabilities are native to the installed version.

### Nginx

- full effective load order from `nginx -T`;
- all `control.orisfy.com` server blocks;
- first effective HTTP and HTTPS block;
- current root proxy;
- current `/admin` handling;
- duplicate or ignored server blocks;
- WebSocket proxy configuration.

Discovery acceptance:

- no config or service mutation;
- no task submission;
- sanitized evidence committed to GitHub;
- final SUMMARY identifies the exact effective route/config and next action.

## 6. Phase 2 — define the OpenClaw-to-ORIS tool contract

Do not route normal development goals through prompt keyword matching.

Minimum tool/action contract:

### `oris_list_projects`

Returns projects authorized for the current identity.

### `oris_create_goal`

Input:

- project key;
- natural-language objective;
- optional constraints;
- optional expected checks.

Output:

- task id;
- canonical status;
- concise user-facing message.

### `oris_get_goal`

Returns:

- canonical status;
- terminal flag;
- failure code;
- progress summary;
- product/evidence SHA when available.

### `oris_cancel_goal`

Only valid before commit/push closure. Must preserve existing cancellation rules.

### `oris_retry_goal`

Only valid for terminal retryable tasks. Creates a new attempt/task id with lineage.

### `oris_confirm_risky_action`

Used only for genuinely risky operations after structured policy classification.

Tool contract requirements:

- machine-readable schema;
- authenticated identity mapping;
- per-project authorization;
- idempotency;
- request/task correlation id;
- body size and timeout limits;
- structured terminal errors;
- no secret values returned;
- no arbitrary shell input.

## 7. Phase 3 — reversible Nginx migration

The migration script must:

1. run as `admin` and use sudo only for host config operations;
2. verify no active task;
3. verify OpenClaw and ORIS service health;
4. use `nginx -T` to identify the effective server block;
5. privately back up every changed Nginx file;
6. generate the candidate config in `/tmp` or private state;
7. route `/` and native UI/WebSocket paths to `127.0.0.1:18789`;
8. preserve restricted `/admin` to `127.0.0.1:18893`;
9. expose the custom shell only under a restricted rollback path;
10. keep intake unexposed;
11. run `nginx -t`;
12. reload Nginx;
13. run loopback and public smoke tests;
14. roll back automatically if any required check fails;
15. verify product repositories remain unchanged;
16. commit sanitized evidence through a detached worktree;
17. print one final SUMMARY.

## 8. Phase 4 — server-side acceptance

Required checks:

- native OpenClaw root HTML loads through public HTTPS;
- static assets load;
- WebSocket handshake succeeds through Nginx;
- OpenClaw auth/pairing flow works;
- Nginx Basic Auth still protects the domain unless explicitly replaced;
- `/admin` remains restricted and functional;
- rollback route loads the custom shell;
- intake remains loopback-only;
- OpenClaw, bridge, intake and Web Console services remain active;
- no product task is submitted;
- no product repository changes.

## 9. Phase 5 — browser acceptance by operator

The operator tests from `https://control.orisfy.com`:

1. native OpenClaw UI is visibly present;
2. create a new conversation;
3. conversation appears in history;
4. switch to another conversation and back;
5. clear/archive/delete an inactive conversation as supported;
6. refresh the page and confirm history persists correctly;
7. confirm no ORIS-specific form fields or raw JSON are required;
8. confirm ordinary conversation does not create a task accidentally.

Do not submit a real product goal until these pass.

## 10. Phase 6 — ORIS tool acceptance

After native UI acceptance:

- enable the stable ORIS tools/actions;
- use a harmless no-product-change tool smoke;
- verify project authorization;
- verify create/status/cancel/retry behavior;
- verify tool errors render naturally in OpenClaw;
- verify one task is created per confirmed goal;
- verify task status is not duplicated repeatedly in the transcript.

## 11. Phase 7 — controlled natural-language product task

Submit one natural-language development goal without ORIS-specific syntax.

Acceptance requires:

- correct project resolution;
- exactly one task;
- Codex preflight pass;
- correct changed-file scope;
- all requested deliverables;
- static/targeted/full tests;
- product commit and matching remote SHA;
- clean product worktree;
- ORIS evidence commit and remote verification;
- terminal `completed`;
- natural-language final response in OpenClaw.

## 12. Repair of the current `/capabilities` task

After migration acceptance, repair the known gap in `oris-final-acceptance-api`:

- add `/capabilities` to the README API list;
- verify the endpoint contract and tests;
- commit and push the documentation repair;
- verify local and remote SHA;
- update ORIS evidence;
- record that the original task was partially complete and the repair closed the missing deliverable.

Do not rewrite product history to pretend the original commit included README.

## 13. Rollback

Rollback must be possible without reinstalling software:

- restore the backed-up effective Nginx config;
- run `nginx -t`;
- reload;
- verify the custom shell root or rollback route;
- verify services remain active;
- preserve OpenClaw and ORIS runtime data;
- record rollback evidence and reason.

## 14. Commercial follow-on priorities

After stable native UI and tools:

1. SSO/OIDC and identity mapping;
2. per-user/tenant/project RBAC;
3. audit retention and privacy controls;
4. rate limiting and abuse prevention;
5. metrics, alerts and SLOs;
6. backup/restore and disaster recovery;
7. generic onboarding and packaging;
8. database-backed task/event ledger;
9. distributed workers and quotas;
10. versioned tool/API compatibility policy.
