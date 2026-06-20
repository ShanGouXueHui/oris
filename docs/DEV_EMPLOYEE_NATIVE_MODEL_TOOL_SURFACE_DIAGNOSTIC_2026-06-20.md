# Native Model Tool Surface Diagnostic — 2026-06-20

**Status: SUPERSEDED**

This document records a rejected intermediate design and is not an execution authority.

## Historical trigger

Controlled retry evidence commit:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

The retry proved that direct Plugin loading and direct typed-tool execution worked, while native Agent telemetry still reported zero `after_tool_call` events.

## Rejected approach

A later intermediate patch attempted to infer the effective model tool surface from native Agent JSON output, including `systemPromptReport` metadata.

That approach is rejected because it:

- requires a model turn before the materialization boundary is known;
- depends on prompt-report output rather than the native Gateway inventory contract;
- creates a competing authority beside `tools.effective`;
- cannot be used when the RPC is unavailable or unsafe.

The corresponding Agent-output parser, aggregation helper, acceptance dependency, and tests must not remain in the active execution path.

## Current authority

The only authorized effective-surface diagnostic is:

- `docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`;
- `scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh`;
- native Gateway RPC `tools.effective`;
- persisted Agent session context;
- zero model turns;
- zero ORIS tool invocations;
- zero product-task submissions;
- exact rollback and final-invariant validation;
- privacy-safe approved-tool presence/count/ownership evidence only.

If `tools.effective` is unavailable or cannot be used safely, the diagnostic must stop and repair that path. Direct invocation, Plugin catalog inspection, or prompt inference must not substitute for it.
