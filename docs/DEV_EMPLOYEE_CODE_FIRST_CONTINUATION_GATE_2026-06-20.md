# Dev Employee Code-First Continuation Gate — 2026-06-20

## 1. Trigger

The user explicitly requires that source-code problems be corrected before further functional debugging or commercialization work, with special emphasis on duplicate function definitions, duplicate variable bindings and competing implementations.

This gate applies to the next conversation and to all changes made after the latest effective-tool-surface diagnostic implementation was added.

## 2. Rule

No OpenClaw runtime mutation, Gateway restart, effective-tool-surface RPC, model turn, ORIS tool invocation or product task may occur until the current `main` source passes a fresh code audit.

A historical `CODE_AUDIT_PASS` is not sufficient after new source files or entrypoints are added.

## 3. Required source scope

At minimum inspect:

- `scripts/dev_employee_openclaw_enable/*.py`;
- `scripts/dev_employee_quality/*.py`;
- `scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh`;
- `scripts/dev_employee_diagnose_openclaw_readonly_policy.sh`;
- `scripts/dev_employee_enable_openclaw_readonly_tools.sh`;
- related configuration under `config/dev_employee/`;
- task authority files under `memory/dev_employee/`;
- any helper imported by the effective-surface diagnostic.

## 4. Mandatory findings

The gate must explicitly check and report:

1. duplicate module/class bindings;
2. duplicate function and class definitions;
3. semantically duplicate function bodies;
4. competing authority implementations;
5. duplicate parsers and validators;
6. duplicate policy/profile expansion logic;
7. duplicate service-control and rollback helpers;
8. duplicate evidence publishers and entrypoints;
9. import cycles;
10. syntax and compile failures;
11. oversized mixed-responsibility modules;
12. hardcoded project, path, host, port, branch, provider, model, runtime version or acceptance-project values;
13. stale legacy execution paths;
14. configuration-contract errors;
15. code/config separation violations.

## 5. Required result

Before runtime work, the authoritative Summary must contain:

```text
RESULT=CODE_AUDIT_PASS
DUPLICATE_BINDINGS=0
AUTHORITY_VIOLATIONS=0
DUPLICATE_FUNCTION_BODIES=0
IMPORT_CYCLES=0
OVERSIZED_MODULES=0
FORBIDDEN_HARDCODING=0
LEGACY_PATH_FINDINGS=0
CONTRACT_ERROR=
OPENCLAW_ACCESSED=NO
GATEWAY_RESTARTED=NO
TASK_SUBMITTED=NO
```

The file count may increase as the package evolves. The pass applies only to the exact commit SHA audited.

## 6. Remediation rules

When a finding exists:

- fix the implementation, not the scanner output;
- preserve only one authority for each rule;
- do not add allowlists that hide genuine duplication;
- distinguish a scanner self-finding from a product hardcoding finding and fix the scanner representation safely;
- split mixed-responsibility files instead of merely raising the line limit;
- move environment-specific values to validated configuration;
- keep generic commercial behavior and avoid final-acceptance-project special cases;
- add positive and negative regression tests for each corrected rule;
- rerun the complete audit after every remediation batch.

## 7. Runtime sequencing after pass

Only after the code audit passes may the project continue with:

1. the effective-tool-surface diagnostic;
2. GitHub evidence review;
3. materialization/session-policy remediation if approved tools are absent;
4. provider/model capability and Harness routing diagnosis if approved tools are present;
5. a separately authorized controlled natural-language acceptance attempt.

A third full read-only enablement is not authorized by this document.

## 8. Evidence and interaction

- long patches and documents are written directly to GitHub;
- host execution uses one short command;
- detailed logs are read from GitHub;
- the user sends only the final Summary;
- no secret, raw config, raw session id, prompt, tool argument/result or private marker content may be printed or committed.
