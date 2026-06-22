# Engineering Guardrails: Script Entry Points and Evidence Handling

Date: 2026-06-22

## Why this memory exists

During Runtime v2 Module A execution, duplicate bootstrap entry points and raw GitHub cache behavior caused confusion. The user explicitly corrected the process: do not create many compatibility scripts or versioned executable entry points. This memory is binding for future chats and future ORIS runtime work.

## Binding rules

1. Maintain exactly one official executable entry point for each operational workflow.
   - For Runtime v2 Module A, the only official script is `scripts/bootstrap_runtime_v2_module_a.sh`.
   - Do not create parallel scripts such as `_v2.sh`, `_v3.sh`, `compat.sh`, `legacy.sh`, or similar executable alternates unless the user explicitly approves a migration plan.

2. Do not keep old executable script copies as backups in the repository.
   - Git history is the backup and rollback mechanism.
   - If a temporary executable script was created, consolidate its logic into the official entry point and delete the duplicate.

3. Avoid branching/version sprawl.
   - Keep the mainline simple.
   - Prefer one official main branch and one official command path.
   - Do not solve assistant memory weaknesses by proliferating branches, scripts, or compatibility layers.

4. Before asking the user to rerun a script, verify the GitHub state.
   - Fetch the official script from GitHub.
   - Confirm the script header/version is the intended official one.
   - Confirm duplicate executable entry points do not remain.

5. Keep terminal output short.
   - Do not ask the user to paste long logs.
   - Scripts should write detailed logs to `reports/execution/` and concise test status to `reports/testing/`.
   - The assistant must read logs and reports from GitHub after evidence is pushed.

6. Failure evidence must still be useful.
   - When practical, failed module runs should commit/push diagnostic evidence to GitHub.
   - If push fails, terminal output should provide only the local evidence path and local commit SHA if available.

7. Prefer dependency-light verification for bootstrap scripts.
   - Use Python standard-library checks where sufficient.
   - Avoid adding external test dependencies for early bootstrap validation unless the module explicitly requires them.

8. Product repository checks must not mutate product worktrees unless the task is explicitly a product task.
   - For Runtime v2 platform validation, use read-only checks such as `git ls-remote` for product repository state.
   - Do not allow local product repo fast-forward/dirty-worktree issues to block ORIS platform Module B/C/etc. unless product mutation is part of the acceptance scope.

## New-chat reminder

At the start of any new ORIS Runtime v2 chat, remind the assistant to obey these rules before proposing commands or uploading scripts:

- one official executable entry point only;
- no compatibility script proliferation;
- Git history is the backup;
- read evidence from GitHub instead of asking the user for long logs;
- do not mutate product repositories during ORIS platform validation unless explicitly required.
