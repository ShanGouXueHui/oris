# ORIS Dev Employee — `agent_end` Policy Addendum

Date: 2026-06-18

## Finding

The second controlled installation reported exactly two runtime hooks although the plugin registers three:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

OpenClaw 2026.5.19 treats `agent_end` as a raw conversation hook. Non-bundled plugins must explicitly set:

`plugins.entries.oris-dev-employee.hooks.allowConversationAccess=true`

Without this scoped policy, OpenClaw accepts the two sanitized telemetry hooks and rejects or omits `agent_end` from the effective runtime registry.

## Decision

Keep `agent_end` because it provides end-to-end agent turn duration, success state and run correlation that cannot be reconstructed reliably from only model and tool durations.

Grant conversation access only to `oris-dev-employee`, not globally.

The plugin handler must continue to persist only:

- timestamp;
- duration;
- success/error boolean;
- provider/model/tool name where applicable;
- SHA-256 hashes of run, call and session identifiers.

It must not persist `event.messages`, prompt text, assistant text, tool arguments, tool results, headers or credentials.

## Installation gate

The v3 installer must verify all of the following after restart:

- the scoped `allowConversationAccess` policy is true;
- exactly three typed hooks are present;
- exactly three approved read-only tools are present;
- all tools remain explicitly denied;
- authentication mode and secret hash are unchanged;
- `tools.allow` is unchanged;
- no write tools are registered;
- queue, product baseline and private listeners are unchanged.

Any failure after mutation must use non-interactive automatic rollback with `openclaw plugins uninstall oris-dev-employee --force` and restore the exact pre-install configuration backup.
