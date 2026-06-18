# ORIS Dev Employee — Current State 2026-06-18

## Executive state

The native OpenClaw UI at `https://control.orisfy.com` is the commercial primary UI.

The native ORIS mixed plugin is installed and enabled. Its three approved read-only tools and three lifecycle telemetry hooks are runtime-verified. The tools remain explicitly denied until controlled read-only enablement and browser acceptance are complete.

No write-side ORIS tool is installed. No product task was submitted during plugin installation.

## Approved architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin and Agent Harness policy adapter
  -> ORIS task governance
  -> Codex real execution
  -> product commit/tests and ORIS evidence returned to OpenClaw
```

The custom ORIS Web Console is restricted to diagnostic/admin use.

## Completed milestones

### Native UI migration

Completed and accepted:

- `/` routes to native OpenClaw;
- new conversation, multiple sessions, history switching, refresh persistence and session deletion were browser-verified;
- `/admin` and `/_oris-chat-shell` remain restricted;
- intake remains private;
- Gateway authentication remains token-based;
- Control UI device pairing is intentionally bypassed for clients already holding a valid Gateway credential.

### Final acceptance product

Repository: `ShanGouXueHui/oris-final-acceptance-api`

Final product commit and remote main:

`bcb93e17ea88704548101f5e4a5c460e15a80ec7`

The `/capabilities` implementation, tests and README API list are complete. Do not submit another task for this completed gap without regression evidence.

### Native plugin validation and installation

Validation evidence commit:

`fadb6275f0a348aed7692f4a910f341f69049363`

Installation task:

`commercial-openclaw-native-plugin-install-20260618`

Final result:

`INSTALLED_TOOLS_DENIED`

Installed plugin:

- id: `oris-dev-employee`
- version: `0.1.0`
- source commit: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

Runtime tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Runtime hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

Current policy:

- plugin enabled with zero plugin errors;
- all three tools remain in `tools.deny`;
- no submit, cancel or retry tool exists;
- `tools.allow` is unchanged;
- Gateway authentication mode and credential are unchanged;
- scoped `allowConversationAccess=true` is enabled only for `oris-dev-employee` so `agent_end` can register;
- plugin telemetry must not persist prompts, messages, assistant text, tool arguments, tool results, headers or credentials.

## Environment truth

### Hosts

- ORIS development/control/execution: `43.106.55.255`, user `admin`
- ORIS path: `/home/admin/projects/oris`
- separate production host: `8.136.28.6`, user `deploy`; do not touch without an explicit production task

### Services

- OpenClaw Gateway: `127.0.0.1:18789`
- enqueue/status API: `127.0.0.1:18891`
- intake API: `127.0.0.1:18892`
- Web Console: `127.0.0.1:18893`
- bridge: `oris-dev-employee-bridge.service`

The 18891 and 18892 services remain loopback-only.

### Runtime and storage

- OpenClaw: `2026.5.19 (a185ca2)`
- Node: `v22.22.2`
- npm: `10.9.7`
- Codex CLI: real coding executor
- Dev Employee task state: filesystem-backed and transaction-hardened
- research store: PostgreSQL database `oris_insight`, schema `insight`, separate from Dev Employee runtime

## Installation safety state

Private marker:

`~/.openclaw/private/oris-dev-employee-plugin-install-current.json`

Pre-install backup:

`/home/admin/.openclaw/backups/native-plugin-install-20260618T205656Z/openclaw.json.before.bak`

Approved rollback wrapper:

`scripts/dev_employee_rollback_openclaw_native_plugin_v2_20260618.sh`

Do not use the older rollback script because its uninstall step can wait on a hidden confirmation prompt.

## Corrected technical conclusions

1. `openclaw plugins validate` is not the authoritative gate for this mixed plugin.
2. Mixed-plugin validation must verify tools, hooks, manifest and runtime contracts through `definePluginEntry`.
3. Runtime inspect reports typed hooks under `typedHooks` and custom hooks under `customHooks`.
4. The first hook count of zero was a parser defect.
5. After parser repair, a count of two was real because `agent_end` required scoped conversation-access policy.
6. The successful v3 install verified all three hooks.
7. Automated uninstall must use `--force`.
8. The 18891 `/latest` 404 was a stale process; refreshing only the enqueue service restored it.

## Current active task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`plugin_installed_tools_denied_pending_controlled_enable`

Current step:

`read_only_readiness_before_readonly_tool_enable`

Objective:

Enable only the three approved read-only tools through OpenClaw policy, verify direct and browser use, verify telemetry and latency observability, and preserve automatic rollback to the tools-denied state.

## Immediate next action

Do not reinstall the plugin and do not enable tools manually.

First create a GitHub-hosted read-only readiness script that verifies:

- install marker and backup validity;
- plugin cold/runtime inventory;
- exact tools and hooks;
- current deny policy and effective allow behavior;
- scoped conversation-access policy;
- Gateway/public UI health;
- telemetry path permissions and sanitized contents;
- queue and product baseline;
- 18891/18892 loopback binding;
- no write tool and no active product task.

Then create a reversible tool-enable script and browser acceptance checklist.

## Commercial priorities

1. accept read-only tools and latency telemetry in native UI;
2. add explicit write actions with approval, project authorization, idempotency and audit;
3. add generic project onboarding and capability discovery;
4. move routine policy/provider management into Admin UI;
5. add monitoring, retention/privacy and disaster recovery;
6. add multi-tenant packaging, quotas and billing boundaries.
