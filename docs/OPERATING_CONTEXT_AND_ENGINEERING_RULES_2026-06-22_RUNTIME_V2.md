# Operating Context and Engineering Rules for Runtime v2

Date: 2026-06-22
Scope: ORIS Autonomous Dev Employee Runtime v2 and subsequent commercial product development.

## Communication and workflow

- Use Chinese for planning, coordination, and status reporting unless a code artifact or external interface requires English.
- Be direct, professional, structured, and evidence-driven.
- Prefer GitHub writes and GitHub evidence over long pasted terminal logs.
- Do not rely on chat history as durable state.
- If commands are needed, provide copy-paste-ready commands.
- Do not use `set -e` in shell commands because it can unexpectedly terminate the user's interactive shell/session.
- Keep commands staged and observable.
- Logs should be written under `/tmp`, `logs/`, or `run/`; only tail relevant sections.

## Environment

### Development / execution host

Current primary execution machine:

```text
Host: 43.106.55.255
User: admin
ORIS path: /home/admin/projects/oris
Expected Codex CLI: installed/authenticated from prior accepted runs
```

Prior durable context classifies this as development host. If the user calls it production in casual language, do not silently reclassify Hangzhou production. Ask or state the distinction if production deployment is involved.

### Production host

```text
Host: 8.136.28.6
User: deploy
Role: production environment
```

Do not touch production host unless the user explicitly authorizes production deployment or production operations.

### Repositories

ORIS platform repo:

```text
ShanGouXueHui/oris
/home/admin/projects/oris
```

Insight product repo:

```text
ShanGouXueHui/oris-commercial-insight-employee
/home/admin/projects/oris-commercial-insight-employee
```

Final acceptance demo product repo:

```text
ShanGouXueHui/oris-final-acceptance-api
/home/admin/projects/oris-final-acceptance-api
```

## Repository boundary

ORIS is the platform repository. It owns:

- orchestration;
- task intake;
- autonomous runtime;
- queues and state;
- registry and governance;
- evidence writing;
- skill resolver;
- deployment verifier;
- platform memory and docs.

Business product application code must live in standalone product repos.

For the insight product, business application code belongs in:

```text
ShanGouXueHui/oris-commercial-insight-employee
```

ORIS may contain demo orchestration and acceptance references to product repos, but not product business logic as mainline application code.

## Branch and release rules

- Use one mainstream branch: `main`.
- Branches/backups are allowed for safety, but avoid unreconciled parallel mainlines.
- Do not leave critical changes only in local working tree.
- Every completed module must be committed and pushed.
- Commit messages should identify module and purpose.

## Engineering standards

- Layered architecture.
- Configuration separated from code.
- Runtime state separated from source code.
- Adapters for external tools: Codex CLI, GitHub, systemd, skills, deployment verifiers.
- Avoid one-off demo scripts as production architecture.
- Preserve compatibility facades when existing imports depend on them.
- Use tests to lock behavior before refactors.
- Favor generic, commercializable design.
- Make policies explicit and machine-checkable.

## Evidence-first module rule

A module is not complete until GitHub contains:

- implementation commit;
- module test plan;
- module test result JSON;
- module execution report;
- evidence index or ORIS run evidence referencing the commit SHA.

Expected files per module:

```text
docs/testing/MODULE_<N>_TEST_PLAN.md
reports/testing/module_<N>_test_result.json
reports/testing/latest_test_result.json
reports/execution/module_<N>_execution_report.md
```

## Testing policy

Default checks:

```text
python -m compileall .
python -m pytest -q
python -m pytest -q -W error
```

Modules may add module-specific tests. Strict-warning mode should pass or the module should explain and fix warnings.

## Skill policy

Skills may be used and downloaded only through a resolver flow:

1. discover candidate;
2. download to quarantine;
3. validate manifest/source;
4. run smoke test;
5. record skill resolution evidence;
6. use only after validation.

Never execute unvalidated downloaded code.

## Human escalation boundary

ORIS should make routine engineering decisions autonomously. It may block only for:

- missing credentials;
- paid resource creation;
- unsafe production operation;
- destructive database operation;
- legal/compliance/security risk;
- repeated unrecoverable failure after bounded repair attempts.

## Deployment and commercial acceptance

For deployable products, required evidence:

```text
reports/deployment/staging_smoke_result.json
reports/deployment/production_smoke_result.json    # only if production is authorized
reports/deployment/commercial_deployment_report.md
reports/acceptance/final_acceptance_report.md
```

A deployment is not successful without smoke tests proving service/endpoint health.

## Current operational caveat

The last attempted SSH bootstrap failed:

```text
admin@43.106.55.255: Permission denied (publickey)
```

This means the command runner did not have SSH key access to `admin@43.106.55.255`. Future remote commands must either be executed from an authenticated terminal/session or after SSH credentials are corrected.
