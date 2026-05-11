# ORIS vNext Architecture — Dev Employee First

Date: 2026-05-11

## 0. Executive decision

ORIS should not immediately replace OpenClaw with Hermes.

Current decision:
- Keep OpenClaw as the access/channel/plugin gateway.
- Do not let OpenClaw own ORIS business logic.
- Do not promote Hermes to the central runtime yet.
- Treat Hermes as a benchmark and optional sidecar experiment for memory/skill-curation ideas.
- Build ORIS vNext around an ORIS-native task kernel, model fabric, memory graph, and execution mesh.

Reasoning:
- OpenClaw already provides working Feishu access, loopback gateway, plugin runtime, provider integration, and Codex-related runtime evolution.
- Hermes is strong in persistent memory, curated memory files, profile isolation, and skill learning, but replacing OpenClaw now would duplicate session, routing, memory, and execution responsibilities.
- The current ORIS weakness is not the access framework itself. The weakness is missing task-kernel discipline, worker-profile separation, execution isolation, and quality evaluation loops.

## 1. Product direction

ORIS remains: Operational Reasoning & Integration System.

The next stage is to turn ORIS from a collection of pipelines and skills into an AI employee operating kernel.

The first employee to complete is:

> Dev Employee — an engineering AI employee that can read the repo, plan changes, execute through Codex CLI or equivalent coding executors, validate, commit, push, and write back logs/docs.

After Dev Employee is stable, other employees should be built by Dev Employee:
- Insight Employee
- Butler Employee
- Delivery/Operations Employee

## 2. Architecture layers

### L1. Access and channel layer

Primary component: OpenClaw.

Responsibilities:
- Feishu / future QQ / web / CLI access
- session ingress and outbound messaging
- plugin/channel runtime
- control UI and gateway
- limited tool exposure

Boundary:
- OpenClaw is the five senses, not the brain.
- It must not own business workflows, research methodology, coding policy, or long-term memory truth.

### L2. ORIS Task Kernel

New central layer.

Responsibilities:
- normalize inbound requests
- classify task type
- bind target project/repo/entity
- select worker profile
- create task_run records
- manage status, retries, failover, and human approval gates
- route to model fabric and execution mesh

Initial task types:
- dev_task
- insight_task
- butler_task
- ops_task
- hybrid_task

Hard rule:
- No long-running execution should happen directly inside the channel handler.
- Channel handlers enqueue or hand off to task kernel only.

### L3. Model Fabric

Reuse and evolve existing ORIS provider orchestration and the free-model module from AIdeal CPS where applicable.

Responsibilities:
- provider registry
- model catalog refresh
- quota/health probe
- scoring and ranking
- active routing generation
- retry then failover
- role-specific routing
- Singapore bridge support when needed

Model role families:
- primary_general
- report_generation
- coding_planning
- coding_execution_support
- cn_candidate_pool
- free_fallback

Rule:
- DeepSeek V4 should enter the candidate pool when available, but must not become the only brain.
- Free providers remain first-class until commercial API budget is approved.

Known provider tokens to support through env/secrets only:
- build.nvidia.com
- Hugging Face
- OpenRouter
- Gemini Flash
- Zhipu
- Ali Bailian
- Tencent Hunyuan

### L4. Memory Graph

ORIS-native memory remains the source of truth.

Memory types:
1. Project Memory
   - GitHub docs
   - handoff files
   - decision records
   - repo conventions

2. Evidence Memory
   - PostgreSQL insight schema
   - sources, snapshots, evidence, metrics, citations

3. Execution Memory
   - task runs
   - plans
   - commands
   - logs
   - validation results
   - failure classifications

4. User/Butler Memory
   - preferences
   - recurring tasks
   - personal workflows

Hermes may be studied as a memory/skill-curation reference, but it should not become the memory source of truth unless a controlled migration proves clear value.

### L5. Execution Mesh

Execution is split from reasoning.

Executor families:
- CodexExecutor
- DeepSeekTUIExecutor
- ShellExecutor
- GitExecutor
- TestExecutor
- InsightPipelineExecutor
- ArtifactExecutor

Initial priority:
- CodexExecutor for development work.
- Direct shell execution is allowed only through controlled scripts and policies.
- All execution must produce logs that can be committed or referenced from GitHub.

### L6. Evaluation and Evolution

ORIS must evaluate work, not just produce output.

Responsibilities:
- validate task completion
- compare model/executor paths
- classify failures
- score result quality
- record improvement actions
- feed successful patterns back into docs/config/skills

Initial evaluation dimensions:
- correctness
- repo compliance
- test pass/fail
- security/secrets safety
- config governance compliance
- delivery quality
- evidence quality for insight tasks

## 3. Dev Employee target behavior

Dev Employee must be able to:
1. read GitHub docs and latest state
2. inspect repo code
3. understand project conventions
4. create a minimal implementation plan
5. execute via Codex CLI or coding executor
6. run syntax/static checks
7. run smoke tests
8. collect logs into repo-friendly paths
9. update docs/handoff
10. commit and push
11. expose a concise result summary

Hard constraints:
- Do not use set -e in user-facing shell scripts.
- Do not hardcode business constants in code.
- Put stable rules in config/ or DB.
- Put secrets only in env/secrets.
- Prefer small steps and reversible changes.
- Write logs to logs/ or run/ and keep screen output short.

## 4. Hermes replacement assessment

### Potential benefits of Hermes
- persistent memory design
- curated memory compaction
- profile isolation
- self-learning skill documents
- local long-running agent workflows

### Replacement risks
- duplicates OpenClaw channel/session responsibilities
- duplicates ORIS provider routing responsibilities
- risks split-brain memory with PostgreSQL/GitHub docs
- increases operational complexity before Dev Employee is stable
- may force large migration before solving the real bottleneck

### Decision
Do not replace OpenClaw now.

Adopt this staged approach:
1. Keep OpenClaw as access layer.
2. Build ORIS-native task kernel and Dev Employee.
3. Add Hermes as sidecar benchmark only after Dev Employee is stable.
4. Compare Hermes sidecar against ORIS-native memory/evolution loops.
5. Replace or integrate only if evidence shows material improvement.

## 5. Implementation phases

### Phase 1 — Architecture documentation and bootstrap
- Add vNext architecture docs.
- Add Dev Employee landing prompt.
- Update README entry points.
- Define task kernel and worker profile config files.

### Phase 2 — Task Kernel scaffold
- Add task schema.
- Add task_run ledger.
- Add worker profile registry.
- Add model role mapping.
- Add log artifact convention.

### Phase 3 — Dev Employee MVP
- Implement DevTask intake.
- Implement repo bootstrap reader.
- Implement CodexExecutor wrapper.
- Implement validation pipeline.
- Implement commit/push policy.
- Implement GitHub log handoff.

### Phase 4 — Self-improvement loop
- Add evaluator.
- Add failure classifier.
- Add improvement backlog writer.
- Add skill/doc update proposal generator.

### Phase 5 — Build other employees through Dev Employee
- Insight Employee vNext
- Butler Employee vNext
- Delivery/Ops Employee vNext

## 6. GitHub-log operating model

Future rule:
- Server execution logs should be written into repo-friendly log summaries or committed diagnostic artifacts when useful.
- New ChatGPT conversations should read GitHub first instead of relying on long pasted logs.
- Runtime noise should not be committed by default.
- Only summarized, decision-useful logs should be committed.

Recommended structure:
- logs/dev_employee/YYYYMMDD/<task_code>.summary.md
- logs/dev_employee/YYYYMMDD/<task_code>.validation.txt
- run/ for local transient files, ignored unless explicitly promoted

## 7. Immediate next implementation target

Build Dev Employee first.

The first landing task in a new conversation should be:
- Read README.md, this vNext architecture doc, and current handoff/state docs.
- Create Phase 2 scaffold: task kernel + worker profile config + Dev Employee execution contract.
- Do not replace OpenClaw.
- Prepare Hermes only as a future sidecar benchmark.
