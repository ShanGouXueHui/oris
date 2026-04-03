# Decision: reset baseline and installation path
Date: 2026-04-03

## Context
The server was reset. ORIS needs a clean and reproducible installation baseline.

## Decisions
1. OpenClaw is installed in the `admin` user environment.
2. OpenClaw is not treated as a Python venv + pip project.
3. A separate Python venv is still created for helper scripts and future repo-side Python tooling.
4. GitHub repo documents are treated as project memory.
5. OpenClaw runtime memory/config remains under `~/.openclaw/`.
6. Repository changes are committed only after validation.
7. Cron-based auto commit/push is explicitly not part of the baseline.

## Consequences
- Lower risk of cross-user runtime confusion
- Easier recovery after server reset
- Cleaner handoff between future sessions
