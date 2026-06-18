# Next Chat Handoff — 2026-06-18

## Mandatory first read

Read in this order before making any design or code change:

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-18.md`
3. `memory/dev_employee/SESSION_ARCHIVE_2026-06-18.md`
4. `memory/dev_employee/OPENCLAW_NATIVE_PLUGIN_INSTALL_COMPLETION_2026-06-18.md`
5. `memory/dev_employee/current_task.json`
6. `memory/dev_employee/current_task.md`
7. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-18.md`
8. `docs/DEV_EMPLOYEE_OPENCLAW_AGENT_END_POLICY_ADDENDUM_2026-06-18.md`
9. `docs/DEV_EMPLOYEE_COMMERCIALIZATION_PRIORITY_2026-06-18.md`
10. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
11. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
12. `orchestration/project_registry.json`

Do not reconstruct the project from chat history after these files are available.

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`plugin_installed_tools_denied_pending_controlled_enable`

Current step:

`read_only_readiness_before_readonly_tool_enable`

## Current installed state

The `oris-dev-employee` plugin is installed and enabled in OpenClaw.

Verified runtime contract:

- tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- plugin errors: zero;
- write tools: absent;
- all three tools: still explicitly denied;
- scoped `allowConversationAccess=true`: enabled for this plugin;
- Gateway authentication: token, unchanged by installation;
- `tools.allow`: unchanged by installation.

Authoritative installation evidence:

- JSON: `logs/dev_employee/openclaw_native_plugin_install/openclaw-native-plugin-install-tools-disabled-20260618T205656Z.json`
- evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

Installed source commit:

`8f174b49196aac90b505846200ce260f75355b41`

Artifact SHA-256:

`976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`

## First action in the new chat

Do not enable tools immediately.

Create a GitHub-hosted read-only readiness script that checks:

1. private install marker and backup validity without printing values;
2. plugin cold/runtime inventory;
3. exact three tools and three hooks;
4. current `tools.deny` entries;
5. effective `tools.allow`, tool profile and agent-specific policy;
6. scoped conversation-access policy;
7. Gateway/direct/public UI health;
8. `/admin` and `/_oris-chat-shell` restricted behavior;
9. 18891 and 18892 loopback-only binding;
10. telemetry path, mode, schema and content-safety scan;
11. active queue count and queue fingerprint;
12. product HEAD, remote main and clean worktree;
13. absence of write tools and product task submission.

The script must be read-only, write detailed logs under `logs/dev_employee/`, commit sanitized evidence through a detached worktree and print one final Summary.

After reading the evidence, design a reversible enablement script. It may remove only the approved three names from the effective deny boundary and may add explicit allow entries only when the discovered policy requires them.

## Browser acceptance target

After controlled enablement, verify in native OpenClaw:

- natural-language request can read current ORIS queue status;
- natural-language request can read latest task status;
- a known task id can be queried;
- no ORIS-specific command syntax is needed;
- no task is submitted;
- queue fingerprint is unchanged;
- no write tool is visible;
- session/history behavior still works;
- telemetry records model, tool and total-agent timing without content leakage;
- response latency is classified from real samples.

On any failure, return automatically to the tools-denied state.

## Do not do

- do not reinstall or upgrade OpenClaw;
- do not reinstall the plugin;
- do not run old v1/v2 install scripts;
- do not edit `openclaw.json` manually;
- do not enable submit/cancel/retry tools;
- do not submit a product task during read-only acceptance;
- do not touch `8.136.28.6`;
- do not put product code in the ORIS repository;
- do not print or commit secrets or private marker content;
- do not ask the user to paste long logs.

## Fixed interaction contract

- Chinese, professional, direct and structured;
- decide routine engineering details without asking the user;
- long scripts/docs/patches go directly to GitHub;
- give one short pull-and-run command;
- no long heredoc;
- user-facing shell scripts do not use `set -e`;
- every user-run script ends with `===== SUMMARY =====`;
- inspect evidence from GitHub;
- `main` is the only mainstream branch;
- backups allowed, competing long-lived branches prohibited;
- layered decoupling, configuration separation and one authoritative source per rule;
- generic commercial design, not acceptance-project hardcoding;
- completion requires tests, exact SHA, remote SHA and evidence.
