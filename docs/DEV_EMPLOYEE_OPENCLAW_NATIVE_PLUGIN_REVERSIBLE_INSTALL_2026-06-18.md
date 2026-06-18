# ORIS Dev Employee — Reversible Native OpenClaw Plugin Installation

Date: 2026-06-18
Status: approved for controlled installation with tools denied

## Preconditions

The installation is allowed only after the isolated validation evidence reports:

- TypeScript build: PASS;
- unit tests: PASS;
- mixed-plugin runtime contract: PASS;
- manifest contract: PASS;
- runtime import: PASS;
- static safety gate: PASS;
- loopback ORIS health, queue and latest routes: PASS;
- no plugin installation or OpenClaw mutation during validation.

Authoritative validation evidence:

`logs/dev_employee/openclaw_native_plugin_validation/openclaw-native-plugin-validation-20260618T153153Z.json`

Evidence commit:

`fadb6275f0a348aed7692f4a910f341f69049363`

## Installation source

Do not install directly from the mutable ORIS worktree.

The installer must:

1. fetch `origin/main`;
2. archive only `orchestration/openclaw_plugins/oris-dev-employee` from the resolved commit;
3. install build dependencies in a temporary directory;
4. compile and rerun tests and mixed-plugin validation;
5. create an npm pack artifact;
6. install the exact artifact using `openclaw plugins install npm-pack:<artifact>`;
7. record the artifact SHA-256 and source commit in private local state and sanitized GitHub evidence.

## Tools-disabled installation state

The plugin must load so that its observation hooks can register, while all three model-facing tools remain unavailable.

Before installation, add these exact names to the existing global `tools.deny` list without removing or reordering existing policy entries:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

OpenClaw tool policy defines deny as higher priority than allow. Therefore the tools remain blocked even if another allow rule or wildcard exists.

Do not add the tools to `tools.allow` during this phase.

## Runtime acceptance

After installation and Gateway restart, verify:

- Gateway service is active;
- direct and public native UI roots return 200 and match;
- plugin appears enabled with no plugin errors;
- runtime inspect exposes exactly the approved three ORIS tools;
- runtime inspect exposes `model_call_ended`, `after_tool_call` and `agent_end` hooks;
- all three tool names remain in global `tools.deny`;
- no write-side ORIS tools exist;
- 18891 and 18892 remain loopback-only;
- queue state is unchanged;
- completed product repository baseline is unchanged;
- Gateway authentication secret and mode are unchanged;
- no product task was submitted.

## Local private state

On success, write a mode-0600 marker:

`~/.openclaw/private/oris-dev-employee-plugin-install-current.json`

The marker may contain:

- plugin id and version;
- source commit;
- npm artifact SHA-256;
- install timestamp;
- exact config backup path;
- denied tool names.

It must not contain tokens, passwords, API keys or raw authentication values.

## Rollback

Rollback must be available before installation.

The rollback procedure is:

1. read the private install marker;
2. confirm the referenced pre-install config backup exists and is mode 0600;
3. run `openclaw plugins uninstall oris-dev-employee` when the plugin is present;
4. restore the exact pre-install `openclaw.json` backup;
5. restart the existing `openclaw-gateway.service`;
6. verify the plugin is absent from cold and runtime inventory;
7. verify public and direct native UI remain healthy;
8. verify queue, product repository and ORIS worktree were not changed;
9. rename the private marker to a rolled-back record;
10. commit sanitized rollback evidence through a detached worktree.

## Failure handling

Any failure after the first configuration mutation must trigger automatic rollback using the same backup. The installer must report whether rollback completed successfully.

## Deferred next phase

A later controlled script may remove the three names from `tools.deny` and add them to the appropriate explicit tool allow policy. That phase must include direct read-only invocation tests and browser acceptance. It must not introduce task submission, cancellation or retry tools.
