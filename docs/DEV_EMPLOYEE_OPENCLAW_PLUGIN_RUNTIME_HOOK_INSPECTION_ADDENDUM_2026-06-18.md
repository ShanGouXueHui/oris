# ORIS Dev Employee — OpenClaw Runtime Hook Inspection Addendum

Date: 2026-06-18

## Final corrected conclusion

Two different problems occurred during plugin installation and must not be conflated:

1. the first runtime hook count of `0` was an ORIS evidence-parser defect;
2. after parser repair, the runtime hook count of `2` was a real OpenClaw policy result because `agent_end` required scoped conversation access.

The final v3 installation corrected both issues and runtime-verified all three approved hooks.

## Runtime inspect field names

In OpenClaw `2026.5.19`, `openclaw plugins inspect <id> --runtime --json` reports typed lifecycle hooks under:

`typedHooks`

Custom hooks are reported under:

`customHooks`

The original installer recognized only generic keys such as `hooks`, `registeredHooks` and `hookNames`. It therefore counted all typed hooks as zero.

The parser must inspect `typedHooks` and `customHooks` explicitly.

## `agent_end` policy gate

After fixing the parser, OpenClaw reported two typed hooks:

- `model_call_ended`
- `after_tool_call`

The missing hook was:

- `agent_end`

For non-bundled plugins, OpenClaw treats `agent_end` as a conversation-access hook. The effective plugin configuration must include:

`plugins.entries.oris-dev-employee.hooks.allowConversationAccess=true`

This policy must be scoped to `oris-dev-employee`, not enabled globally.

The plugin implementation must continue to discard conversation content and persist only bounded timing/status metadata and hashed identifiers.

## Final runtime gate

For the ORIS mixed plugin, installation acceptance must verify:

- exact tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- exact typed hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- plugin enabled and plugin error count zero;
- scoped `allowConversationAccess=true`;
- all three tools still denied during installation acceptance;
- no submit, cancel or retry tool;
- authentication mode and credential unchanged;
- `tools.allow` unchanged;
- queue and product baseline unchanged.

Final successful installation evidence:

- JSON: `logs/dev_employee/openclaw_native_plugin_install/openclaw-native-plugin-install-tools-disabled-20260618T205656Z.json`
- evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`
- runtime tool count: `3`
- runtime hook count: `3`

## Rollback correction

OpenClaw plugin uninstall requires interactive confirmation unless `--force` is supplied. When command output is redirected to a log, the confirmation prompt appears to the operator as a silent hang.

All automated and explicit rollback paths must use:

`openclaw plugins uninstall oris-dev-employee --force`

Approved rollback entry:

`scripts/dev_employee_rollback_openclaw_native_plugin_v2_20260618.sh`

Do not use the older rollback script.

## Current next phase

The plugin is already installed and enabled. Do not reinstall it.

The next phase is controlled read-only tool enablement and browser smoke testing. It must begin with a read-only readiness check of the effective tool policy and must preserve automatic rollback to the tools-denied state.
