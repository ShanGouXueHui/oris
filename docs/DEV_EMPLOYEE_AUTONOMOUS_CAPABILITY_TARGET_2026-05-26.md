# ORIS Dev Employee Autonomous Capability Target — 2026-05-26

## Target

ORIS Dev Employee should be able to receive a development task and autonomously complete the loop:

```text
understand task
  -> read durable context
  -> decide whether more capabilities/skills are needed
  -> safely discover/download candidate skills if needed
  -> design an implementation plan
  -> use Codex CLI for code changes
  -> run local checks
  -> iterate on failures
  -> let host bridge perform final checks and GitHub verification
  -> persist evidence and status
```

## Current proven foundation

Already verified:

1. local HTTP enqueue API;
2. local enqueue client;
3. systemd bridge service;
4. Codex CLI execution through the bridge;
5. runtime task contract injection;
6. host-side checks;
7. product GitHub push/remote verification;
8. ORIS evidence commit/push;
9. read-only skill discovery/audit/intelligence extraction.

Key evidence commits:

- `7c861d3f2db084a8ac9724e954d51d2d79a8667d` — HTTP enqueue smoke completed.
- `776b7bb90666e562dc5b3e15fa6a902ff1790d38` — runtime task contract injection completed.
- `f1161efa323cc764ca7ef2ac56da69640a6f06ee` — enqueue client smoke completed.

## Gap to close

The current bridge executes one prompt reliably. The next gap is the autonomous work loop inside the Codex task:

- plan before coding;
- detect missing capabilities;
- use existing ORIS-owned scripts before external skills;
- download third-party skills only into quarantine;
- never install unreviewed third-party skills into runtime;
- run tests and repair failures before returning `local_checks_passed`;
- produce structured evidence that explains design, changes, checks, blockers, and follow-up work.

## Capability layers

### Layer 1 — Intake and execution

Implemented:

- `scripts/dev_employee_enqueue_server.py`
- `scripts/dev_employee_enqueue_client.py`
- `scripts/dev_employee_supervised_bridge_v2.py`
- `oris-dev-employee-enqueue.service`
- `oris-dev-employee-bridge.service`

### Layer 2 — Autonomous task prompt

Needed now:

- a reusable autonomous development prompt template;
- a local helper that creates runtime task prompts and enqueues them;
- a standard result schema for plan/design/test/repair evidence.

### Layer 3 — Skill resolver

Partially implemented:

- `scripts/skill_candidate_audit.py`
- `scripts/skill_policy_report.py`
- `scripts/skill_intelligence_extract.py`

Needed next:

- a skill resolver command that maps task requirements to ORIS-owned capabilities first;
- if missing, downloads candidates only into quarantine;
- writes a recommendation report instead of installing automatically.

### Layer 4 — Self-repair and escalation

Needed next:

- structured failure taxonomy;
- automatic retry limits;
- repair loop for test failures;
- blocked status when policy/security/network constraints prevent completion.

## Non-negotiable boundaries

- No product code inside `/home/admin/projects/oris`.
- No secrets, `.env`, private keys, `.venv`, caches, or runtime queue files in GitHub.
- No direct production installation of third-party skills.
- No pseudo execution evidence.
- Completion requires GitHub-verifiable ORIS evidence.
