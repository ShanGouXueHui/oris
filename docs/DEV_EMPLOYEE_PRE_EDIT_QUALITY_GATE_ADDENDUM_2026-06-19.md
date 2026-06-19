# Dev Employee Pre-Edit Quality Gate Addendum

Date: 2026-06-19
Status: mandatory engineering policy
Scope: ORIS / OpenClaw / Codex-backed AI Dev Employee

## 1. Mandatory order of operations

Before modifying an existing engineering file, the executor must:

1. read the current task and authoritative project registry;
2. run the repository quality scanner against the current `main` state;
3. inspect findings for the intended target files and their authoritative configuration sources;
4. confirm that the proposed change will not create another definition, another authority source, or another embedded environment value;
5. split an oversized target before adding a new responsibility;
6. only then modify files.

The pre-edit scan is a blocking engineering step, not optional documentation.

## 2. Duplicate definition policy

A duplicate definition means the same symbol, key, rule, configuration authority, or responsibility is defined more than once in the same effective scope.

The following are defects:

- duplicate Python top-level function or class names in one module;
- duplicate top-level JavaScript or TypeScript declarations in one module;
- duplicate shell function names in one script;
- duplicate JSON keys;
- the same environment or business rule maintained by multiple authoritative configuration files;
- copied implementation blocks that perform the same responsibility independently.

The following are not duplicates by themselves:

- local variables with the same name in different functions;
- constants with the same conventional name in independent scripts;
- runtime records that repeat task IDs, commit IDs, project names, or historical evidence.

## 3. Hardcoding policy

Runtime-dependent values must not be embedded in executable source code. This includes:

- absolute host paths;
- listener addresses and deployment ports;
- public domains;
- task IDs and acceptance-project names;
- commit SHAs used as operating inputs;
- passwords, tokens, API keys, private keys, cookies, credentials, or authorization headers.

Environment values belong in an authoritative configuration or registry. Secrets must be represented only by secret references and resolved from private runtime storage. Secret values must never enter GitHub evidence, logs, summaries, or chat output.

## 4. Large-file policy

A file above the configured threshold is not an automatic proof of bad design, but it is a blocking signal before adding another responsibility.

For an oversized active source file, the executor must:

- identify cohesive responsibilities;
- extract configuration, transport, validation, telemetry, persistence, or evidence concerns into separate modules;
- preserve one public entrypoint where appropriate;
- keep product-specific behavior out of shared orchestration modules;
- test the extracted boundaries before declaring completion.

Generated data, provider snapshots, historical sessions, queues, run records, and evidence files are not source modules and must not be mechanically split or rewritten by the source-quality gate.

## 5. Scanner accuracy requirements

The scanner must fail closed on syntax errors and plaintext secrets, but it must avoid destructive false positives.

Required scanner behavior:

- inspect only top-level definitions for duplicate-symbol checks;
- exclude generated runtime directories and timestamped runtime JSON;
- do not treat same-named constants in independent files as duplicate definitions;
- do not record secret values in findings;
- apply source hardcoding checks to executable code, while treating configuration as the intended authority layer;
- report active source files separately from historical operational scripts and generated data.

## 6. Completion evidence

A change is not complete until evidence shows:

- pre-edit scan executed;
- target findings reviewed;
- post-edit scan executed;
- no new findings introduced;
- relevant tests passed;
- commit SHA and remote `main` SHA match;
- evidence contains no secret or conversation content.
