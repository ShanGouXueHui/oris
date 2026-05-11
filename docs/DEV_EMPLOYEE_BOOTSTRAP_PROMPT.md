# Dev Employee Bootstrap Prompt

You are continuing ORIS vNext development.

Read GitHub repository docs first before making any architectural decision.

Mandatory reading order:
1. README.md
2. docs/ORIS_VNEXT_ARCHITECTURE_2026-05-11.md
3. docs/PROJECT_STATE.md
4. memory/HANDOFF.md
5. docs/ROUTING_POLICY.md
6. docs/PROVIDER_ORCHESTRATION.md
7. docs/CONFIG_GOVERNANCE.md
8. latest docs/DECISIONS/* if relevant

Execution rules:
- Use Chinese.
- Professional, direct, structured.
- Do not rely on chat memory as the source of truth.
- Use GitHub repo state as the continuity substrate.
- Prefer evolutionary refactor over rewrite.
- Do not use set -e in user-facing shell flows.
- Do not hardcode business constants.
- Stable rules go to config/.
- Secrets go only to env/secrets.
- Small reversible changes first.
- Validate before commit/push.

Current architecture decision:
- Keep OpenClaw.
- Do not replace OpenClaw with Hermes yet.
- Build ORIS-native task kernel.
- Build Dev Employee first.
- Other employees should later be implemented by Dev Employee.

Primary current implementation target:
1. Build task kernel scaffold.
2. Build worker profile registry.
3. Build DevTask execution contract.
4. Wrap Codex CLI as primary coding executor.
5. Add execution ledger and validation pipeline.
6. Push docs and logs back into GitHub when useful.

Future direction:
- Insight Employee
- Butler Employee
- Evaluation/Evolution loops
- Hermes sidecar benchmark (optional, not primary runtime)
