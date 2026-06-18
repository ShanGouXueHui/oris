# ORIS Dev Employee — Native OpenClaw Plugin Installation Completion

Date: 2026-06-18

## Result

Task `commercial-openclaw-native-plugin-install-20260618` is complete with result:

`INSTALLED_TOOLS_DENIED`

The ORIS native OpenClaw mixed plugin is installed and enabled, but all model-facing ORIS tools remain explicitly denied pending controlled read-only enablement and browser acceptance.

## Installed artifact

- plugin id: `oris-dev-employee`
- plugin version: `0.1.0`
- source commit: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- installed OpenClaw version: `2026.5.19 (a185ca2)`
- Node: `v22.22.2`
- npm: `10.9.7`

Authoritative evidence:

- JSON: `logs/dev_employee/openclaw_native_plugin_install/openclaw-native-plugin-install-tools-disabled-20260618T205656Z.json`
- log: `logs/dev_employee/openclaw_native_plugin_install/openclaw-native-plugin-install-tools-disabled-20260618T205656Z.log`
- evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

## Build and runtime verification

Passed:

- dependency installation;
- strict TypeScript build;
- unit tests;
- mixed-plugin runtime contract validation;
- deterministic npm pack creation;
- plugin installation and enablement;
- Gateway restart and health checks;
- public root/direct root equality;
- plugin runtime inspection;
- secret scan;
- remote evidence SHA verification.

Runtime contract:

- exactly 3 approved read-only tools;
- exactly 3 approved typed hooks;
- 0 plugin errors;
- no write-side ORIS tools.

Tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

## Current policy state

The three tools are present in the plugin runtime but remain explicitly blocked by global `tools.deny`.

The scoped plugin policy is enabled:

`plugins.entries.oris-dev-employee.hooks.allowConversationAccess=true`

This policy is required for the non-bundled `agent_end` hook. The plugin implementation still persists only bounded telemetry fields and hashes; it must not persist prompts, conversation messages, assistant text, tool arguments, tool results, headers or credentials.

Gateway authentication remains token-based. The authentication mode and secret hash were unchanged by installation. `tools.allow` was unchanged.

## Backup and rollback

A pre-install configuration backup was created at:

`/home/admin/.openclaw/backups/native-plugin-install-20260618T205656Z/openclaw.json.before.bak`

The current private install marker is:

`~/.openclaw/private/oris-dev-employee-plugin-install-current.json`

It is local-only, mode `0600`, and must not be committed or printed.

Use only the non-interactive rollback wrapper for future rollback:

`scripts/dev_employee_rollback_openclaw_native_plugin_v2_20260618.sh`

Do not use the older rollback script because its hidden interactive uninstall confirmation can appear to hang.

## Safety verification

Confirmed unchanged:

- ORIS queue state;
- ORIS main worktree state;
- product repository baseline;
- Gateway authentication secret;
- `tools.allow` policy;
- product task count.

Confirmed private:

- enqueue/status service on `127.0.0.1:18891`;
- intake service on `127.0.0.1:18892`.

No product task was submitted. OpenClaw was not reinstalled or upgraded.

## Corrections learned during installation

1. `openclaw plugins validate` validates simple tool-plugin metadata and is not the correct gate for the ORIS mixed plugin built with `definePluginEntry`.
2. Runtime typed hooks are reported under `typedHooks`; custom hooks are under `customHooks`.
3. A hook count of zero in the first installer was a parser defect.
4. After parser repair, a hook count of two was real: `agent_end` required scoped `allowConversationAccess=true`.
5. Automated plugin uninstall must use `--force` because redirected output hides the interactive confirmation prompt.
6. The `/latest` route existed in GitHub but the active 18891 process was stale; refreshing only `oris-dev-employee-enqueue.service` restored it without queue mutation.

## Next controlled phase

Create and execute a reversible read-only enablement flow that:

1. verifies the installed marker, backup, plugin runtime, current deny policy, Gateway health, queue and product baseline;
2. removes only the approved three names from `tools.deny` and adds them to the correct explicit allow policy only if the effective policy requires it;
3. keeps all write actions absent;
4. restarts the existing Gateway;
5. performs direct and native-browser read-only tool smoke tests;
6. confirms no task submission or queue mutation;
7. confirms telemetry contains `model_call_ended`, `after_tool_call` and `agent_end` records without message or secret content;
8. measures time-to-first-token and total response duration where the installed runtime exposes them;
9. automatically returns to the tools-denied state on any failure.
