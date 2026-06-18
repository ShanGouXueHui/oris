# Current AI Dev Employee Task

Status: `plugin_installed_tools_denied_pending_controlled_enable`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `read_only_readiness_before_readonly_tool_enable`

## Objective

Enable only the three approved read-only ORIS tools through the installed native OpenClaw plugin, verify natural-language use and latency telemetry in the native UI, and preserve automatic rollback to the tools-denied state.

This task does not authorize any submit, cancel, retry or product-mutation tool.

## Completed prerequisite

The native plugin installation task is complete:

- previous task: `commercial-openclaw-native-plugin-install-20260618`
- result: `INSTALLED_TOOLS_DENIED`
- plugin id: `oris-dev-employee`
- version: `0.1.0`
- source commit: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

Authoritative evidence:

`logs/dev_employee/openclaw_native_plugin_install/openclaw-native-plugin-install-tools-disabled-20260618T205656Z.json`

## Current runtime contract

Installed and enabled tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Installed typed hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

Verified:

- plugin errors: `0`;
- exactly 3 tools and 3 hooks;
- write tools absent;
- all three tools remain explicitly denied;
- `tools.allow` unchanged at installation;
- scoped `allowConversationAccess=true` enabled for `oris-dev-employee`;
- Gateway authentication mode and credential unchanged at installation;
- queue and product baseline unchanged;
- no product task submitted;
- 18891 and 18892 remain loopback-only.

## Safety state

Private marker:

`~/.openclaw/private/oris-dev-employee-plugin-install-current.json`

Pre-install backup:

`/home/admin/.openclaw/backups/native-plugin-install-20260618T205656Z/openclaw.json.before.bak`

Approved rollback wrapper:

`scripts/dev_employee_rollback_openclaw_native_plugin_v2_20260618.sh`

Do not use the old rollback script and do not reinstall the plugin.

## First required action

Create a GitHub-hosted read-only readiness script. It must not modify configuration, restart services, enable tools, invoke a write action or submit a product task.

It must verify:

1. marker and backup validity, ownership and mode without printing secret values;
2. plugin cold/runtime inventory and exact tools/hooks;
3. current `tools.deny` entries and effective `tools.allow`/profile/agent policy;
4. scoped conversation-access policy;
5. Gateway, public root, `/admin`, rollback route and loopback listeners;
6. telemetry file location, permissions and sanitized record schema;
7. active queue count and queue fingerprint;
8. product HEAD, remote SHA and clean worktree;
9. absence of write tools and product task submission.

Detailed output goes to `logs/dev_employee/` and sanitized evidence is committed through a detached worktree. The script ends with `===== SUMMARY =====`.

## Controlled enablement after readiness evidence

After reviewing the evidence, build a reversible enablement script that:

- changes only the effective policy entries required to expose the three approved tools;
- keeps write tools absent;
- validates configuration before restarting the existing Gateway;
- directly tests all three read-only tools;
- performs native browser acceptance using natural language;
- confirms no queue mutation and no product task submission;
- confirms telemetry contains model, tool and agent timing records without content leakage;
- records TTFT and total duration where supported;
- automatically restores the tools-denied state on failure.

## Do not do

- do not reinstall or upgrade OpenClaw;
- do not reinstall the plugin;
- do not manually edit `openclaw.json`;
- do not run the old v1/v2 installation scripts;
- do not enable write tools;
- do not touch the production host `8.136.28.6`;
- do not reopen the completed final acceptance product task without regression evidence;
- do not print tokens, passwords, keys or private marker contents.

## Commercial sequence after this task

1. accept read-only tools and latency telemetry;
2. design explicit write actions with approval, project authorization, idempotency and audit;
3. add generic project onboarding and capability discovery;
4. move routine provider/policy management into Admin UI;
5. complete monitoring, privacy/retention and disaster-recovery gates;
6. add multi-tenant quotas and commercial packaging.
