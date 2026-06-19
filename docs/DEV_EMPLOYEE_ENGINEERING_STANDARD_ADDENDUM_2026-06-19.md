# ORIS Dev Employee Engineering Standard Addendum — 2026-06-19

This addendum supplements:

- `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
- `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`

It is authoritative where earlier documents are silent or conflict.

## 1. Mandatory pre-edit discovery gate

Before modifying any source, configuration, script or durable documentation file, the implementation process must inspect the relevant repository scope for:

1. an existing implementation of the requested behavior;
2. duplicate function, class, schema, constant, route, policy or config definitions;
3. duplicated authoritative rules across code, scripts, config and docs;
4. hardcoded project, repository, path, branch, host, port, provider, model, credential name, runtime version or acceptance-only condition;
5. oversized files already mixing multiple responsibilities;
6. generated/runtime artifacts that should not be edited as source.

The edit may proceed only after deciding which existing definition is authoritative.

Do not add a second implementation merely because the first implementation was difficult to locate.

## 2. Duplicate-definition prohibition

Duplicate definitions are defects when they independently encode the same behavior or rule.

Prohibited examples:

- two parsers for the same OpenClaw CLI JSON shape;
- multiple profile-expansion tables for the same runtime version;
- repeated project path/commit constants in separate scripts;
- duplicate route definitions for the same API endpoint;
- parallel retry/terminal-state classifications;
- copied tool-name lists that can drift;
- separate documentation files both claiming to be the current authority without an explicit hierarchy.

Required response to a duplicate:

1. identify the authoritative definition;
2. migrate callers to it;
3. remove or deprecate the duplicate;
4. add a regression/static check where practical;
5. update the context index when document authority changes.

## 3. Hardcoding prohibition

Shared commercial code must not hardcode environment-specific or acceptance-specific values.

Values must come from an appropriate authority:

- project identity/path/branch: `orchestration/project_registry.json` or task payload;
- stable non-secret platform configuration: version-controlled config/schema;
- runtime host/service values: environment or deployment config;
- provider/model selection: provider policy/config and runtime discovery;
- secrets: local secret store/environment references only;
- test-only examples: fixtures clearly isolated from production code;
- OpenClaw version-specific behavior: an explicit versioned compatibility map with validation and a failure for unknown versions.

A literal value is acceptable only when it is a protocol constant, schema constant or intentionally versioned compatibility value. The reason must be evident from module placement or documentation.

Do not special-case `oris-final-acceptance-api` or any other acceptance repository in shared ORIS logic.

## 4. Large-file decomposition gate

A file must be split when it owns more than one independent responsibility or when continued editing would make review and rollback unsafe.

Required decomposition pattern:

- pure schema/domain logic;
- policy calculation;
- runtime adapters;
- process/service control;
- validation;
- evidence/reporting;
- CLI/entrypoint orchestration.

Operational scripts should orchestrate modules rather than contain all parsing, policy, process control, evidence and rollback logic inline.

New code must not make an already oversized file materially less maintainable. Refactor first when necessary.

## 5. Configuration mutation standard

Before replacing an active service configuration:

1. build the candidate in a private temporary path;
2. validate JSON/schema syntax;
3. run the installed runtime's own config validation command where available;
4. verify only authorized fields changed;
5. scan candidate lists/maps for duplicate entries;
6. back up the exact active config privately;
7. capture pre-mutation service PID and health;
8. activate atomically;
9. restart/reload only the existing service named by the approved task;
10. verify health and required runtime inventory;
11. on failure, capture bounded sanitized status/journal evidence before rollback;
12. restore exactly and prove health.

A unit test of a Python config builder is not proof that the target runtime accepts the generated configuration.

## 6. OpenClaw tool-policy compatibility standard

OpenClaw tool enablement must distinguish:

- plugin registration;
- optional plugin-tool materialization;
- global allow/deny policy;
- active profile filtering;
- `alsoAllow` profile extension;
- Agent-specific policy;
- skill visibility;
- actual model tool invocation.

Do not infer a later stage from an earlier stage:

- registered does not mean materialized;
- materialized does not mean profile-authorized;
- profile-authorized does not mean visible to the selected Agent/model;
- skill-visible does not mean tool-invoked;
- direct tool invocation does not mean model invocation.

Each stage requires its own evidence.

Version-specific profile expansions must be configured once, validated for duplicate entries, and rejected for unknown OpenClaw versions rather than guessed.

## 7. Service-failure diagnostics

When a controlled restart fails, evidence must capture, before rollback where safely possible:

- failure stage;
- validator command and return code;
- systemd active/sub state;
- bounded recent journal lines;
- error class and field path;
- whether the port was bound;
- whether the old PID exited;
- whether the public and loopback health checks failed;
- whether rollback restored the service.

Never commit raw configuration, tokens, environment files or unbounded journals.

## 8. Tri-state evidence semantics

A boolean `false` must not be used for both:

- a check that ran and failed; and
- a check that never ran because an earlier stage aborted.

Evidence schemas must represent at least:

- `PASS` / true;
- `FAIL` / false;
- `NOT_CHECKED` or null.

Summaries must not describe a `NOT_CHECKED` invariant as an observed regression.

This applies to:

- write-tool absence;
- queue unchanged;
- product unchanged;
- direct tool calls;
- telemetry privacy;
- runtime inventory;
- remote SHA verification.

## 9. Quality-scanner policy

Repository quality scans must separate:

1. active source findings;
2. legacy operational-script findings;
3. generated/runtime artifact findings;
4. intentional evidence/documentation content;
5. false positives caused by scanner policy.

Generated/runtime artifacts must not inflate active engineering findings.

A target quality gate may pass while repository-wide legacy debt remains. Both facts must be reported explicitly.

Scanner fixes must not merely suppress a true defect. Every exclusion requires a category rationale.

## 10. Skill and plugin lifecycle

Required skills/plugins may be installed, upgraded or removed when needed for the approved architecture.

Rules:

- inspect the current installed version and source first;
- do not reinstall as a generic troubleshooting shortcut;
- remove obsolete or shadowing copies;
- validate runtime visibility for the selected Agent;
- back up and roll back atomically;
- record source commit/artifact hash where applicable;
- keep write capabilities separate from read-only capabilities;
- never install unreviewed third-party execution skills into the commercial path.

## 11. Automatic operator workflow

The system should complete deterministic engineering and acceptance steps automatically.

Do not make the user manually copy internal tool commands into a browser or paste long logs into chat.

The preferred workflow is:

1. assistant writes scripts/docs/patches directly to GitHub;
2. user receives one short pull-and-run command only when host execution is required;
3. script runs preflight, mutation, tests, rollback and evidence publication automatically;
4. detailed logs are committed as sanitized evidence;
5. user sends only the final Summary;
6. assistant reads evidence from GitHub.

## 12. Completion and branch policy

- `main` remains the only mainstream branch.
- Backups and detached evidence worktrees are allowed.
- Competing long-lived branches are prohibited.
- Do not append to tracked evidence after its commit.
- A completed platform change requires source commit, remote verification, real runtime tests and durable evidence.
- A rollback-successful failed attempt is a safe failure, not a completed feature.
