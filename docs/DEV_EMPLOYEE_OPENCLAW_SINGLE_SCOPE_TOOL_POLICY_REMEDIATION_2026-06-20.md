# OpenClaw Single-Scope Tool Policy Remediation — 2026-06-20

## Trigger

Diagnostic evidence commit:

`366c8b441e8adff5fa684b2255339ad32832cc31`

The private candidate passed ORIS static policy compatibility but failed the installed OpenClaw `config patch --dry-run` validator.

The rejected candidate contained both:

- non-empty `tools.allow`;
- non-empty `tools.alsoAllow`.

OpenClaw `2026.5.19 (a185ca2)` defines these fields as mutually exclusive within the same policy scope. The runtime schema requires one of these modes:

1. an explicit `allow` list; or
2. a tool `profile` plus additive `alsoAllow` entries.

## Root cause

The previous ORIS transform tried to prove two separate ideas simultaneously:

- materialize the `coding` profile expansion into `tools.allow`;
- authorize the three optional ORIS plugin tools through `tools.alsoAllow`.

That combination is not accepted by the installed OpenClaw schema.

This was a policy-semantic defect, not a duplicate-definition, import-cycle, hardcoding or Gateway health defect.

## Correct policy selection

The active baseline has:

- `tools.profile = coding`;
- no non-empty `tools.allow`;
- no non-empty `tools.alsoAllow`;
- the three approved ORIS tools in `tools.deny`.

The corrected candidate therefore uses:

- existing `tools.profile = coding` unchanged;
- no materialized `tools.allow`;
- `tools.alsoAllow` containing only:
  - `oris_queue_status`;
  - `oris_task_status`;
  - `oris_latest_task_status`;
- the three approved tools removed from `tools.deny`.

The expected minimal policy patch changes only:

- `tools.alsoAllow`;
- `tools.deny`.

If a future valid baseline already has a non-empty `tools.allow`, ORIS extends that list and does not create `tools.alsoAllow`.

## Code enforcement

The implementation now enforces:

- non-empty `allow` and non-empty `alsoAllow` cannot coexist;
- current-baseline transformation preserves the `coding` profile and uses only `alsoAllow`;
- candidate compatibility fails before runtime validation when both scopes are active;
- rollback scope reconstruction supports either accepted mode;
- marker evidence records a single authorization scope;
- OpenClaw JSON dry-run output is summarized into privacy-safe rule codes and hashes without storing raw messages or SecretRef identifiers.

## Safety boundary

The next run remains diagnostic-only.

It must not:

- replace the active configuration;
- restart Gateway;
- install the routing Skill;
- invoke ORIS tools;
- submit a product task;
- add write tools;
- touch the production host.

A passing dry-run authorizes GitHub evidence review only. It does not authorize automatic activation.
