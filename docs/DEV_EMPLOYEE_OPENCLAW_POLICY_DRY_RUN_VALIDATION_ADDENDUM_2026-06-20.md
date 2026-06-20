# OpenClaw Policy Dry-run Validation Addendum — 2026-06-20

## Trigger

Diagnostic evidence commit `7c01b72a8ae71c2cbf62a0ae4032ab245b09335c` proved that the installed OpenClaw CLI exposes `config validate` and `config check`, but neither command accepts an alternate candidate configuration path.

This is not a policy rejection. It means those two commands cannot safely validate a private candidate without replacing the active configuration.

## Runtime-compatible validation path

The installed runtime is OpenClaw `2026.5.19 (a185ca2)`.

The matching OpenClaw source and CLI documentation define:

```text
openclaw config patch --file <patch> --dry-run
```

`config patch --dry-run` applies the proposed operations to the in-memory active configuration, runs schema and policy validation on the post-change configuration, and does not write `openclaw.json`.

`--replace-path` is repeatable and is used only when an array or object must be replaced exactly rather than recursively merged.

## ORIS implementation

The diagnostic now builds a private, mode-0600 policy-delta patch containing only the configuration paths changed by the authoritative ORIS policy transforms:

- `tools.profile`;
- `tools.allow`;
- `tools.alsoAllow`;
- `tools.deny`;
- `agents.defaults.skills`, when changed;
- `agents.list`, only when an agent-specific Skill list must change, with exact replacement through `--replace-path agents.list`.

Unrelated tool configuration, Gateway configuration, Provider/Model configuration, credentials and other top-level configuration domains are not copied into the patch.

The validator:

1. discovers `config patch` and its flags from the installed CLI;
2. requires `--file` and `--dry-run`;
3. requires `--replace-path` only when the generated patch needs exact list replacement;
4. optionally uses `--json` when available;
5. hashes the active config before and after validation;
6. accepts the validation only when the CLI returns success and the active config hash is unchanged;
7. records only command return code, output byte counts, output hash, diagnostic categories and sanitized patch metadata;
8. never records patch content, candidate content, raw CLI output or secret values.

## Safety boundary

The next diagnostic run remains pre-activation only.

It must not:

- replace the active config;
- restart Gateway;
- install the routing Skill;
- invoke an ORIS tool;
- submit a product task;
- add a write tool;
- touch the production host.

A `PASS` result authorizes evidence review only. It does not automatically authorize candidate activation.

A `FAIL` result means the installed OpenClaw dry-run validator rejected the policy delta; the evidence must be read before remediation.

## Entrypoint

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

Return only the final `===== SUMMARY =====` block. Detailed evidence is read from GitHub.
