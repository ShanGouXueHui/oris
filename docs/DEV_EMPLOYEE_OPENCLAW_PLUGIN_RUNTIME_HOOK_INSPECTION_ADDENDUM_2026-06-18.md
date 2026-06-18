# ORIS Dev Employee — OpenClaw Runtime Hook Inspection Addendum

Date: 2026-06-18

## Finding

The first controlled installation successfully loaded the ORIS plugin and exposed the approved three read-only tools, but the installer classified the runtime hook count as zero.

That classification was caused by the ORIS evidence parser, not by proof that OpenClaw failed to register the hooks.

In OpenClaw 2026.5.19, `openclaw plugins inspect <id> --runtime --json` reports typed lifecycle hooks under the camel-case field:

`typedHooks`

Custom hooks are reported under:

`customHooks`

The original installer parser recognized only generic keys such as `hooks`, `registeredHooks` and `hookNames`. It therefore counted the three typed hooks as zero even though the native inspect contract explicitly includes typed hook reporting.

## Correct runtime gate

For the ORIS mixed plugin, runtime acceptance must parse:

- `tools` for the exact optional tool contract;
- `typedHooks` for `model_call_ended`, `after_tool_call` and `agent_end`;
- `customHooks` when present;
- plugin enabled/error state;
- absence of submit, cancel and retry tools.

The expected typed hooks remain:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

## Rollback correction

OpenClaw plugin uninstall requires interactive confirmation unless `--force` is supplied. Because ORIS scripts redirect command output to a log, an interactive uninstall prompt appears to the operator as a silent hang.

All automated rollback paths must therefore use:

`openclaw plugins uninstall oris-dev-employee --force`

The existing successful manual rollback remains valid. Future automatic and explicit rollback execution must use the non-interactive v2 wrappers.

## Reinstallation rule

Reinstallation is allowed only after the previous marker has been archived by a verified rollback and the native UI, queue, product baseline and private loopback bindings remain healthy.

The v2 installer patches only the runtime hook evidence parser and automatic rollback confirmation behavior. It does not change plugin source, tool policy, authentication, task submission behavior or product repositories.
