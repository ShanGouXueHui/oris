#!/usr/bin/env bash

# ORIS Runtime v2 Module A bootstrap script.
# Policy: do not use `set -e`; keep terminal output short; write evidence to GitHub-friendly files.

ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
PRODUCT_DIR="${PRODUCT_DIR:-$WORKDIR/oris-commercial-insight-employee}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_A_COMMIT_AND_PUSH:-1}"
MODULE0_SHA="7d1d604b92b21f1213f990140b3345b4be2163ca"

mkdir -p "$WORKDIR"

summary() {
  printf '%s\n' "$1"
}

fail_short() {
  summary "FAILED: $1"
  if [ -n "$LOG_FILE" ]; then
    summary "Log: $LOG_FILE"
  fi
  exit 1
}

clone_or_update_repo() {
  repo_url="$1"
  repo_dir="$2"
  branch="$3"
  label="$4"

  if [ ! -d "$repo_dir/.git" ]; then
    git clone "$repo_url" "$repo_dir" >> "$LOG_FILE" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
      fail_short "cannot clone $label"
    fi
  else
    cd "$repo_dir" || fail_short "cannot enter $label repo"
    git fetch origin >> "$LOG_FILE" 2>&1
    git checkout "$branch" >> "$LOG_FILE" 2>&1
    git pull --ff-only origin "$branch" >> "$LOG_FILE" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
      fail_short "cannot fast-forward $label repo"
    fi
  fi
}

# Prepare ORIS repo and log location first.
TEMP_LOG="/tmp/oris_module_A_bootstrap_$$.log"
LOG_FILE="$TEMP_LOG"
summary "ORIS Runtime v2 Module A bootstrap starting..."
clone_or_update_repo "$ORIS_REPO_URL" "$ORIS_DIR" "$BRANCH" "ORIS"

cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo"
mkdir -p reports/execution
LOG_FILE="reports/execution/module_A_bootstrap_latest.log"
{
  echo "# Module A bootstrap log"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "oris_dir=$ORIS_DIR"
  echo "product_dir=$PRODUCT_DIR"
  echo "branch=$BRANCH"
  echo ""
  echo "# pre-clone log"
  if [ -f "$TEMP_LOG" ]; then
    cat "$TEMP_LOG"
  fi
} > "$LOG_FILE" 2>&1
rm -f "$TEMP_LOG"

clone_or_update_repo "$PRODUCT_REPO_URL" "$PRODUCT_DIR" "$BRANCH" "product"

cd "$ORIS_DIR" || fail_short "cannot return to ORIS repo"
BASE_SHA="$(git rev-parse HEAD 2>> "$LOG_FILE")"
PRODUCT_HEAD="$(cd "$PRODUCT_DIR" && git rev-parse HEAD 2>> "$ORIS_DIR/$LOG_FILE")"

{
  echo ""
  echo "# repository state"
  echo "base_sha=$BASE_SHA"
  echo "product_head=$PRODUCT_HEAD"
  if [ "$PRODUCT_HEAD" = "$MODULE0_SHA" ]; then
    echo "product_module_state=module_0_only"
  else
    echo "product_module_state=has_commits_after_module_0"
    echo "product_commits_after_module0:"
    cd "$PRODUCT_DIR" && git log --oneline "$MODULE0_SHA"..HEAD
    cd "$ORIS_DIR" || exit 0
  fi
  echo ""
  echo "# required context file existence"
} >> "$LOG_FILE" 2>&1

for f in \
  memory/dev_employee/CURRENT_STATE_2026-06-22_AUTONOMOUS_RUNTIME_V2.md \
  memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-22_AUTONOMOUS_RUNTIME_V2.md \
  docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md \
  docs/OPERATING_CONTEXT_AND_ENGINEERING_RULES_2026-06-22_RUNTIME_V2.md \
  docs/DEV_EMPLOYEE_FINAL_ACCEPTANCE_2026-06-22.md \
  memory/dev_employee/CURRENT_STATE_2026-06-22_POST_ACCEPTANCE.md \
  orchestration/project_registry.json \
  memory/dev_employee/current_task.json \
  memory/dev_employee/current_task.md
 do
  if [ -f "$f" ]; then
    echo "OK $f" >> "$LOG_FILE"
  else
    echo "MISSING $f" >> "$LOG_FILE"
  fi
done

mkdir -p docs/runtime_v2 schemas/runtime_v2 tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_A_TEST_PLAN.md <<'EOF'
# Module A Test Plan - Runtime v2 Architecture and State Machine

## Scope

Validate the Runtime v2 Module A architecture and state machine design.

## Test Targets

1. State machine schema exists and is valid JSON.
2. Required runtime states are present.
3. Required transition paths are present.
4. Terminal states reject further transitions.
5. Approval-gated states are explicit.
6. Failure states are classified into retryable, blocked, and fatal categories.

## Acceptance

Module A passes only when transition tests pass and execution evidence is written to:

- `reports/testing/module_A_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_A_execution_report.md`
EOF

cat > schemas/runtime_v2/state_machine.schema.json <<'EOF'
{
  "version": "runtime_v2_module_A",
  "states": [
    "RECEIVED",
    "PLANNED",
    "READY",
    "RUNNING",
    "WAITING_APPROVAL",
    "REPAIRING",
    "TESTING",
    "COMMITTING",
    "COMPLETED",
    "FAILED_RETRYABLE",
    "FAILED_BLOCKED",
    "FAILED_FATAL",
    "CANCELLED"
  ],
  "terminal_states": [
    "COMPLETED",
    "FAILED_FATAL",
    "CANCELLED"
  ],
  "transitions": [
    ["RECEIVED", "PLANNED"],
    ["PLANNED", "READY"],
    ["READY", "RUNNING"],
    ["RUNNING", "WAITING_APPROVAL"],
    ["RUNNING", "TESTING"],
    ["RUNNING", "FAILED_RETRYABLE"],
    ["FAILED_RETRYABLE", "REPAIRING"],
    ["REPAIRING", "TESTING"],
    ["TESTING", "COMMITTING"],
    ["COMMITTING", "COMPLETED"],
    ["WAITING_APPROVAL", "RUNNING"],
    ["WAITING_APPROVAL", "FAILED_BLOCKED"],
    ["RECEIVED", "CANCELLED"],
    ["PLANNED", "CANCELLED"],
    ["READY", "CANCELLED"],
    ["RUNNING", "CANCELLED"],
    ["WAITING_APPROVAL", "CANCELLED"],
    ["REPAIRING", "CANCELLED"],
    ["TESTING", "CANCELLED"],
    ["COMMITTING", "CANCELLED"],
    ["FAILED_RETRYABLE", "CANCELLED"],
    ["FAILED_BLOCKED", "CANCELLED"]
  ]
}
EOF

cat > tests/runtime_v2/test_state_machine_transitions.py <<'EOF'
import json
from pathlib import Path

SCHEMA_PATH = Path("schemas/runtime_v2/state_machine.schema.json")


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_exists_and_has_required_keys():
    schema = load_schema()
    assert "states" in schema
    assert "terminal_states" in schema
    assert "transitions" in schema


def test_required_states_exist():
    schema = load_schema()
    states = set(schema["states"])
    required = {
        "RECEIVED",
        "PLANNED",
        "READY",
        "RUNNING",
        "WAITING_APPROVAL",
        "REPAIRING",
        "TESTING",
        "COMMITTING",
        "COMPLETED",
        "FAILED_RETRYABLE",
        "FAILED_BLOCKED",
        "FAILED_FATAL",
        "CANCELLED",
    }
    assert required.issubset(states)


def test_required_transitions_exist():
    schema = load_schema()
    transitions = {tuple(item) for item in schema["transitions"]}
    required = {
        ("RECEIVED", "PLANNED"),
        ("PLANNED", "READY"),
        ("READY", "RUNNING"),
        ("RUNNING", "WAITING_APPROVAL"),
        ("RUNNING", "TESTING"),
        ("RUNNING", "FAILED_RETRYABLE"),
        ("FAILED_RETRYABLE", "REPAIRING"),
        ("REPAIRING", "TESTING"),
        ("TESTING", "COMMITTING"),
        ("COMMITTING", "COMPLETED"),
        ("WAITING_APPROVAL", "RUNNING"),
        ("WAITING_APPROVAL", "FAILED_BLOCKED"),
    }
    assert required.issubset(transitions)


def test_terminal_states_have_no_outgoing_transitions():
    schema = load_schema()
    terminal_states = set(schema["terminal_states"])
    transitions = {tuple(item) for item in schema["transitions"]}
    outgoing_from_terminal = [
        transition for transition in transitions if transition[0] in terminal_states
    ]
    assert outgoing_from_terminal == []


def test_every_transition_uses_declared_states():
    schema = load_schema()
    states = set(schema["states"])
    for source, target in schema["transitions"]:
        assert source in states
        assert target in states
EOF

cat > docs/runtime_v2/FAILURE_TAXONOMY_MODULE_A.md <<'EOF'
# Runtime v2 Module A Failure Taxonomy

## Retryable

- DEPENDENCY_INSTALL_FAILED
- CODEX_EXECUTION_FAILED
- TEST_FAILED
- SCHEMA_VALIDATION_FAILED
- GITHUB_WRITE_FAILED

## Blocked

- ENVIRONMENT_ACCESS_BLOCKED
- MISSING_CREDENTIAL
- APPROVAL_REQUIRED
- SECURITY_OR_COMPLIANCE_BLOCKED

## Fatal

- NON_RECOVERABLE_REPEATED_FAILURE
EOF

cat > docs/runtime_v2/ACCEPTANCE_CRITERIA_MODULE_A.md <<'EOF'
# Runtime v2 Module A Acceptance Criteria

Module A is accepted when:

1. Architecture document exists.
2. State machine schema exists.
3. Failure taxonomy exists.
4. Status transition tests pass.
5. Testing plan exists.
6. Test result JSON exists.
7. `latest_test_result.json` points to Module A result.
8. Execution report exists and records commit SHA after commit.
EOF

cat > docs/runtime_v2/ARCHITECTURE_AND_STATE_MACHINE_MODULE_A.md <<'EOF'
# Runtime v2 Module A - Architecture and State Machine Design

## Objective

Define ORIS Autonomous Dev Employee Runtime v2 as a persistent AI development employee runtime.

## Control Plane

OpenClaw Web is only the control plane. It submits goals, shows status, and approves high-risk actions. It must not be the long-running execution runtime.

## Execution Plane

The autonomous worker / agent loop is the execution plane. It performs planning, implementation, tests, repair, evidence writing, and GitHub commit workflow.

## Platform Boundary

ORIS contains platform runtime, governance, evidence, orchestration, state, approval, and recovery logic. Business product code must live in product repositories.

## Core Runtime Components

1. Goal intake and immutable run creation.
2. Module planner and compact context-pack generator.
3. Persistent queue and run-state store.
4. Bounded autonomous worker loop.
5. Approval gate for high-risk actions.
6. Failure classifier and repair policy.
7. Evidence writer for tests, execution reports, deployment reports, and acceptance records.
8. GitHub integration for commits, issue updates, and durable audit trail.

## State Machine

The canonical state machine is stored in:

- `schemas/runtime_v2/state_machine.schema.json`

## Failure Handling

Failure categories are stored in:

- `docs/runtime_v2/FAILURE_TAXONOMY_MODULE_A.md`

## Module A Non-Goals

- No business insight product code.
- No production deployment.
- No credential handling.
- No paid resource provisioning.
EOF

summary "Generated Module A files. Running tests quietly..."
python -m pytest tests/runtime_v2 -q >> "$LOG_FILE" 2>&1
PYTEST_RC=$?

if [ "$PYTEST_RC" -eq 0 ]; then
  TEST_STATUS="passed"
else
  TEST_STATUS="failed"
fi

export PYTEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA LOG_FILE
python - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path

pytest_rc = int(os.environ.get("PYTEST_RC", "1"))
status = os.environ.get("TEST_STATUS", "failed")
base_sha = os.environ.get("BASE_SHA", "")
product_head = os.environ.get("PRODUCT_HEAD", "")
module0_sha = os.environ.get("MODULE0_SHA", "")
log_file = os.environ.get("LOG_FILE", "")

result = {
    "module": "Runtime v2 Module A",
    "status": status,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "pytest_exit_code": pytest_rc,
    "base_sha": base_sha,
    "product_repo_head": product_head,
    "product_repo_module0_sha": module0_sha,
    "old_interactive_insight_product_continued": False,
    "log_file": log_file,
    "checks": [
        "schema_exists",
        "required_states_exist",
        "required_transitions_exist",
        "terminal_states_have_no_outgoing_transitions",
        "every_transition_uses_declared_states",
    ],
}

Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_A_test_result.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
Path("reports/testing/latest_test_result.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
PY

cat > reports/execution/module_A_execution_report.md <<EOF
# Runtime v2 Module A Execution Report

## Module

Architecture and State Machine Design

## Base Commit

$BASE_SHA

## Product Repository Check

- Product repo head: $PRODUCT_HEAD
- Module 0 expected commit: $MODULE0_SHA
- Old interactive insight product continued: no

## Test Command

\`python -m pytest tests/runtime_v2 -q\`

## Test Result

- pytest exit code: $PYTEST_RC
- status: $TEST_STATUS

## Evidence Files

- \`docs/runtime_v2/ARCHITECTURE_AND_STATE_MACHINE_MODULE_A.md\`
- \`schemas/runtime_v2/state_machine.schema.json\`
- \`docs/runtime_v2/FAILURE_TAXONOMY_MODULE_A.md\`
- \`docs/runtime_v2/ACCEPTANCE_CRITERIA_MODULE_A.md\`
- \`tests/runtime_v2/test_state_machine_transitions.py\`
- \`docs/testing/MODULE_A_TEST_PLAN.md\`
- \`reports/testing/module_A_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_A_bootstrap_latest.log\`

## Module A Commit SHA

Pending until commit step completes.
EOF

if [ "$PYTEST_RC" -ne 0 ]; then
  summary "Module A tests failed. No commit pushed. See $ORIS_DIR/$LOG_FILE"
  exit "$PYTEST_RC"
fi

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests passed. Commit/push skipped by ORIS_MODULE_A_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $ORIS_DIR/$LOG_FILE"
  exit 0
fi

git add \
  docs/runtime_v2/ARCHITECTURE_AND_STATE_MACHINE_MODULE_A.md \
  schemas/runtime_v2/state_machine.schema.json \
  docs/runtime_v2/FAILURE_TAXONOMY_MODULE_A.md \
  docs/runtime_v2/ACCEPTANCE_CRITERIA_MODULE_A.md \
  tests/runtime_v2/test_state_machine_transitions.py \
  docs/testing/MODULE_A_TEST_PLAN.md \
  reports/testing/module_A_test_result.json \
  reports/testing/latest_test_result.json \
  reports/execution/module_A_execution_report.md \
  reports/execution/module_A_bootstrap_latest.log >> "$LOG_FILE" 2>&1

if git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
  summary "Tests passed. No file changes to commit."
  summary "Log: $ORIS_DIR/$LOG_FILE"
  exit 0
fi

git commit -m "runtime-v2(module-a): add architecture and state machine design" >> "$LOG_FILE" 2>&1
COMMIT_RC=$?
if [ "$COMMIT_RC" -ne 0 ]; then
  fail_short "git commit failed"
fi

MODULE_COMMIT_SHA="$(git rev-parse HEAD 2>> "$LOG_FILE")"
python - <<PY >> "$LOG_FILE" 2>&1
from pathlib import Path
p = Path("reports/execution/module_A_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until commit step completes.", "$MODULE_COMMIT_SHA")
p.write_text(text, encoding="utf-8")
PY

git add reports/execution/module_A_execution_report.md >> "$LOG_FILE" 2>&1
git commit -m "runtime-v2(module-a): record execution commit sha" >> "$LOG_FILE" 2>&1
REPORT_COMMIT_RC=$?
if [ "$REPORT_COMMIT_RC" -ne 0 ]; then
  fail_short "execution report commit failed"
fi

FINAL_SHA="$(git rev-parse HEAD 2>> "$LOG_FILE")"
git push origin "$BRANCH" >> "$LOG_FILE" 2>&1
PUSH_RC=$?
if [ "$PUSH_RC" -ne 0 ]; then
  summary "Tests passed and local commits created, but push failed. See $ORIS_DIR/$LOG_FILE"
  exit "$PUSH_RC"
fi

summary "DONE: Runtime v2 Module A committed and pushed."
summary "Commit: $FINAL_SHA"
summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_A_execution_report.md"
