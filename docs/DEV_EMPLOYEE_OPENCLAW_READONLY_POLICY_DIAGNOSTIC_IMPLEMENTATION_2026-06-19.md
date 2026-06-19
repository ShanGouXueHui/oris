# OpenClaw Read-only Policy Diagnostic Implementation — 2026-06-19

## Scope

This implementation addresses the failed read-only tool enablement at the exact pre-runtime stage where the existing OpenClaw Gateway did not become healthy after candidate configuration activation.

It does not redesign ORIS, reinstall or upgrade OpenClaw, reinstall the plugin, authorize a write tool, submit a product task, or touch the production host.

## Entrypoint

`scripts/dev_employee_diagnose_openclaw_readonly_policy.sh`

The entrypoint runs the GitHub-hosted Python diagnostic and prints one final `===== SUMMARY =====` block.

## Diagnostic-only safety boundary

The diagnostic run:

- reads the current tools-denied configuration;
- captures the existing Gateway active state, PID presence and HTTP health;
- captures the queue and product repository baseline;
- constructs a validation-safe candidate under a mode-0700 temporary directory;
- redacts sensitive candidate values before writing the temporary validation artifact;
- applies the existing authoritative profile-tool and Skill policy transformations to that private candidate;
- does not replace the active OpenClaw configuration;
- does not restart the Gateway;
- does not invoke ORIS tools;
- does not submit or mutate a task;
- removes the temporary candidate after evidence creation.

## Source authority and layering

The implementation reuses the existing authorities:

- `context.py` for runtime facts and paths;
- `profile_tool_policy.py` for `tools.allow`, `tools.alsoAllow` and `tools.deny` transformation;
- `agent_skill_policy.py` for Agent Skill visibility;
- `policy.py` for the active enablement policy contract;
- `evidence.py` for detached-worktree evidence publication.

Responsibilities are separated into:

- candidate policy compatibility;
- installed-runtime validator discovery;
- Gateway service control and failure diagnostics;
- Gateway HTTP/direct-tool adapter;
- plugin runtime inventory;
- diagnostic baseline and invariants;
- candidate construction;
- diagnostic orchestration;
- enablement activation;
- native acceptance and final invariants;
- reporting and evidence.

## Candidate validation

Static compatibility checks cover:

- `tools.profile`;
- `tools.allow` uniqueness and profile-group materialization;
- `tools.alsoAllow` uniqueness and active-profile authorization;
- approved tools removed from `tools.deny`;
- group selector syntax;
- default Agent resolution;
- routing Skill visibility.

The installed OpenClaw CLI is then inspected for a safe alternate-config validator. Only a validator exposing an explicit candidate-path flag is executed. The diagnostic does not run a validator that can only read the active configuration.

Validator evidence contains only command outcome metadata, output byte counts, output hashes and bounded diagnostic categories. It does not contain raw configuration or raw command output.

## Controlled activation failure capture

The existing enablement path now uses the shared service controller.

Before restart it records the baseline service state. If restart or the health gate fails, it captures, before rollback:

- bounded `systemctl --user status` rows;
- bounded `journalctl --user` rows;
- return codes;
- output byte counts;
- output hashes;
- post-failure service state.

Sensitive lines are dropped or redacted. Raw configuration, credentials and private marker content are not recorded.

Rollback restores the exact backed-up tools-denied configuration and then uses the same service controller to prove Gateway health.

## Evidence semantics

Checks and stages use:

- `PASS` — executed and accepted;
- `FAIL` — executed and rejected;
- `NOT_CHECKED` — intentionally not executed or blocked by an earlier failure.

A diagnostic-only run marks activation, runtime inventory, direct tool calls, native Agent acceptance, telemetry acceptance and rollback as `NOT_CHECKED`.

## Result handling

Possible primary results are:

- `DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW`;
- `DIAGNOSTIC_RUNTIME_VALIDATION_FAILED`;
- `DIAGNOSTIC_VALIDATOR_UNAVAILABLE`;
- `DIAGNOSTIC_FAILED`;
- `DIAGNOSTIC_EVIDENCE_PUBLISH_FAILED`.

No enablement retry is authorized until the resulting GitHub evidence is read and a minimal runtime-accepted policy is selected from observed facts.

## Server execution

Run once on the ORIS development/control/execution host after pulling `main`:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

Only the final summary should be returned to chat. Detailed evidence is read from GitHub.
