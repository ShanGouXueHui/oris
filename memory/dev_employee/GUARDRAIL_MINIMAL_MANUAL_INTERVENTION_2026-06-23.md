# Guardrail: Minimal Manual Intervention

Date: 2026-06-23

This memory is binding for future ORIS Runtime v2 work.

## Rule

Continue automatically whenever the work can be completed through GitHub-side updates, documentation, script preparation, report verification, or memory updates.

Do not ask the user for confirmation at every module boundary.

Only interrupt the user when a step requires the user's authenticated server or local environment, such as running the official bootstrap script that performs local tests and pushes evidence.

When manual execution is required, provide exactly one short copy-paste command block, keep terminal output short, and then read the resulting evidence from GitHub.
