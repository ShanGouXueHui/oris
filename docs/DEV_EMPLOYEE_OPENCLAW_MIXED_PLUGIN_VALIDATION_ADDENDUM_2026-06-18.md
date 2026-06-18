# ORIS Dev Employee — Mixed OpenClaw Plugin Validation Addendum

Date: 2026-06-18

This addendum corrects the validation gate in `DEV_EMPLOYEE_OPENCLAW_NATIVE_PLUGIN_DESIGN_2026-06-18.md`.

## Finding

In OpenClaw 2026.5.19, `openclaw plugins validate` is an authoring command for **simple tool plugins**. It imports the entry and requires metadata produced by `defineToolPlugin`.

The ORIS plugin is intentionally a **mixed native plugin** built with `definePluginEntry` because one entry must register both:

- three optional read-only ORIS tools;
- `model_call_ended`, `after_tool_call` and `agent_end` telemetry hooks.

Therefore `openclaw plugins validate` is not an applicable gate for this package. Converting the package to `defineToolPlugin` solely to satisfy that CLI would remove the required hooks and violate the approved architecture.

## Replacement gate

The isolated validator must run all of the following:

1. TypeScript strict compilation against the installed OpenClaw 2026.5.19 SDK;
2. unit tests for configuration, loopback restrictions, sanitization and telemetry hashing;
3. mixed-plugin runtime contract validation by importing the built `definePluginEntry` object and registering it against a non-executing mock API;
4. exact runtime tool set validation;
5. exact runtime hook set validation;
6. optional-tool validation in runtime registration and manifest metadata;
7. manifest id, config schema and package extension validation;
8. explicit absence of submit, cancel and retry tools;
9. static GET-only and secret-boundary checks;
10. verification that OpenClaw config, Gateway PID, queue, ORIS worktree and product repository remain unchanged.

The mixed-plugin validator does not invoke tools or hooks, does not contact a model, does not install the plugin and does not alter OpenClaw configuration.

## Installation gate remains deferred

Passing isolated mixed-plugin validation does not authorize installation. Installation requires a separate reversible script with configuration backup, tools initially unallowed, runtime inspection, read-only smoke tests and rollback verification.
