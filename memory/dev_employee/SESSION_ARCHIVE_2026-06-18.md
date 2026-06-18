# ORIS Dev Employee — Session Archive 2026-06-18

## Purpose

This archive captures the decisions, investigations, failures, corrections and final state from the long commercialization session that continued the native OpenClaw UI migration into a stable native ORIS plugin.

It is historical context. Current operational truth is in `CURRENT_STATE_2026-06-18.md` and `current_task.json`.

## Starting point

The session began after the native OpenClaw UI migration had already been completed and accepted:

- `https://control.orisfy.com/` served the native OpenClaw UI;
- `/admin` served the restricted ORIS Web Console;
- `/_oris-chat-shell` retained the restricted custom rollback shell;
- token authentication remained enabled;
- device pairing was intentionally bypassed for authenticated Control UI clients;
- native conversation creation, history, switching, refresh persistence and session deletion had passed browser acceptance;
- the final acceptance product README gap was completed and pushed at `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

The next commercial objective was to replace prompt-keyword routing with a stable native OpenClaw tool/plugin contract and to establish latency telemetry.

## Plugin discovery

Read-only discovery against the installed OpenClaw runtime confirmed:

- OpenClaw version `2026.5.19 (a185ca2)`;
- Node `v22.22.2`;
- npm `10.9.7`;
- native plugin CLI and SDK support;
- `definePluginEntry` support;
- typed tool registration;
- typed lifecycle hooks including `model_call_ended`, `after_tool_call` and `agent_end`;
- no existing ORIS plugin;
- no active product task;
- public and direct OpenClaw roots healthy;
- suitable lifecycle hooks for response-latency observability.

The approved plugin shape became a mixed native plugin: tools plus lifecycle hooks in one `definePluginEntry` entry.

## Plugin implementation

The plugin was implemented under:

`orchestration/openclaw_plugins/oris-dev-employee/`

Approved read-only tools:

- `oris_queue_status` -> `GET /queue`
- `oris_task_status` -> `GET /task/{task_id}`
- `oris_latest_task_status` -> `GET /latest`

Approved telemetry hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

Security and data rules:

- loopback HTTP only;
- bounded request and response sizes;
- GET-only ORIS access;
- sanitized tool results;
- no task submission/cancel/retry tools;
- telemetry writes only bounded metadata and SHA-256 identifier hashes;
- no prompt, message, assistant text, tool argument, tool result, header or credential persistence.

## TypeScript validation iterations

Several strict typing failures were corrected using evidence-driven minimal changes:

1. configuration schema was wrapped with OpenClaw's JSON plugin schema helper;
2. tool results received required `details` metadata;
3. unknown tool parameters were narrowed before reading `task_id`;
4. all tools received required human-readable `label` fields;
5. optional `configSchema` and `register` members were narrowed before invocation;
6. the mixed-plugin validator was moved from TypeScript source into runtime JavaScript so test-only typing did not block production compilation.

No fix changed the approved tool names, GET-only boundary, optional-tool status or telemetry scope.

## Validator correction

The initial isolated validator used:

`openclaw plugins validate`

That was incorrect for this plugin shape. In OpenClaw `2026.5.19`, that command validates simple `defineToolPlugin` metadata. The ORIS plugin uses `definePluginEntry` because it must register both tools and hooks.

The final validation gate instead:

- builds TypeScript strictly;
- runs unit tests;
- imports the built mixed-plugin entry;
- registers it against a non-executing mock API;
- checks exact tools and hooks;
- checks optional status and labels;
- checks manifest/package contracts;
- confirms absence of write tools;
- checks static safety and loopback APIs;
- verifies no OpenClaw, queue or product mutation.

## Stale 18891 service process

The first full validation passed all plugin gates but failed because `GET /latest` on `127.0.0.1:18891` returned 404.

GitHub source already implemented `/latest`. A controlled diagnostic confirmed the active systemd process was using the authoritative script but had not loaded the current route implementation.

Only `oris-dev-employee-enqueue.service` was restarted. Results:

- `/latest`: 404 -> 200;
- `/health`: 200;
- `/queue`: 200;
- service remained loopback-only;
- queue unchanged;
- OpenClaw Gateway PID unchanged;
- product baseline unchanged.

The complete isolated validation then passed with result `VALIDATED_NOT_INSTALLED` and evidence commit `fadb6275f0a348aed7692f4a910f341f69049363`.

## First installation attempt and interrupted marker

A reversible installer was created to:

- rebuild from immutable `origin/main` source;
- rerun tests and mixed-plugin validation;
- create an npm pack artifact;
- back up `openclaw.json`;
- add the three tools to `tools.deny`;
- install and enable the plugin;
- restart the Gateway;
- inspect runtime tools/hooks;
- roll back automatically on failure.

A later attempt found an existing private marker. A read-only diagnostic classified the state as `INTERRUPTED_AFTER_MUTATION`:

- marker state `installing`;
- valid pre-install backup;
- plugin installed and enabled;
- tools denied;
- three tools present;
- runtime hook parser reported zero hooks;
- current config differed from backup.

The correct response was rollback, not marker deletion.

## Hidden interactive rollback prompt

The first rollback appeared to hang because the script redirected output from:

`openclaw plugins uninstall oris-dev-employee`

OpenClaw waited for an interactive confirmation that was hidden in the log redirection. After the operator entered `y`, rollback completed successfully.

Permanent correction:

- all automated and explicit rollback paths use `openclaw plugins uninstall oris-dev-employee --force`;
- the approved rollback entry is `scripts/dev_employee_rollback_openclaw_native_plugin_v2_20260618.sh`.

## Runtime hook parser correction

The first installer parser looked only for generic `hooks`, `registeredHooks` and `hookNames` fields. OpenClaw runtime inspect reports typed lifecycle hooks under `typedHooks` and custom hooks under `customHooks`.

The zero-hook result was therefore a parser defect. The parser was updated to include both native fields.

## Second installation attempt: two hooks

After parser correction, installation reached runtime inspection with:

- plugin enabled;
- zero plugin errors;
- three tools present;
- two hooks present;
- no write tools;
- Gateway/public UI healthy.

This was not another parser bug. The missing hook was `agent_end`.

OpenClaw classifies `agent_end` as a raw conversation hook for non-bundled plugins. It requires:

`plugins.entries.oris-dev-employee.hooks.allowConversationAccess=true`

The installer correctly treated the missing hook as a contract failure and automatically rolled back. The rollback was healthy.

## Conversation-access decision

The project retained `agent_end` because it provides end-to-end agent-run duration, success/error status and run correlation that cannot be reliably reconstructed from only model-call and tool-call timings.

The scoped conversation-access policy was approved only for `oris-dev-employee`.

This is not permission to persist conversation content. The implementation continues to discard `event.messages` and persists only bounded telemetry metadata and hashed identifiers.

## Successful v3 installation

The v3 installer added:

- scoped `allowConversationAccess=true`;
- exact verification of that policy;
- typed hook parsing;
- non-interactive rollback;
- unchanged authentication and `tools.allow` gates;
- tools-denied verification;
- no-write-tool verification.

Final result:

`INSTALLED_TOOLS_DENIED`

Final runtime state:

- plugin enabled;
- plugin errors: 0;
- runtime tools: 3;
- runtime hooks: 3;
- tools contract matches;
- hooks contract matches;
- write tools absent;
- approved tools still denied;
- authentication mode token;
- authentication credential unchanged;
- `tools.allow` unchanged;
- queue unchanged;
- ORIS worktree unchanged;
- product baseline unchanged;
- enqueue/status and intake remain loopback-only;
- no product task submitted;
- no OpenClaw reinstall or upgrade.

Installed source:

`8f174b49196aac90b505846200ce260f75355b41`

Artifact SHA-256:

`976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`

Installation evidence:

- JSON: `logs/dev_employee/openclaw_native_plugin_install/openclaw-native-plugin-install-tools-disabled-20260618T205656Z.json`
- log: `logs/dev_employee/openclaw_native_plugin_install/openclaw-native-plugin-install-tools-disabled-20260618T205656Z.log`
- evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

## Current private recovery state

Private marker:

`~/.openclaw/private/oris-dev-employee-plugin-install-current.json`

Pre-install backup:

`/home/admin/.openclaw/backups/native-plugin-install-20260618T205656Z/openclaw.json.before.bak`

These remain local-only and mode `0600`.

## Current task transition

Completed task:

`commercial-openclaw-native-plugin-install-20260618`

New active task:

`commercial-openclaw-readonly-tool-enable-20260618`

Current step:

`read_only_readiness_before_readonly_tool_enable`

The next phase must not reinstall the plugin. It must inspect the effective tool policy, then enable only the three approved read-only tools through a reversible config change and browser smoke test.

## Required next acceptance

The next acceptance must verify:

- natural-language OpenClaw use of queue/latest/task status tools;
- no ORIS-specific command syntax required;
- no task submission or queue mutation;
- no write tool visible;
- native UI sessions remain healthy;
- authentication and restricted routes remain healthy;
- telemetry records model, tool and agent durations without content leakage;
- time-to-first-token and total duration baseline where supported;
- automatic return to tools-denied state on failure.

## Fixed working contract

- read GitHub persistent context before work;
- Chinese, professional, direct and structured communication;
- no routine engineering choices delegated to the user;
- long scripts/docs/patches written directly to GitHub;
- short pull-and-run command only;
- no long terminal heredoc;
- detailed logs stored under `logs/dev_employee/` and read from GitHub;
- every user-run script ends with one `===== SUMMARY =====`;
- no secrets in logs, summaries, GitHub or chat;
- no `set -e` in user-facing scripts;
- `main` is the only mainstream branch;
- backups allowed, competing long-lived branches prohibited;
- ORIS contains platform/evidence; product code remains in product repositories;
- layered decoupling, configuration separation and one authoritative source per rule;
- generic commercial mechanisms, not acceptance-project hardcoding;
- completion requires exact deliverables, tests, commit SHA, remote SHA and evidence.
