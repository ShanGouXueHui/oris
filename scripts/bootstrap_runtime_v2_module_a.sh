#!/usr/bin/env bash

# ORIS Runtime v2 Module A official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-22-runtime-v2-module-a-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_A_COMMIT_AND_PUSH:-1}"
MODULE0_SHA="7d1d604b92b21f1213f990140b3345b4be2163ca"
LOG_FILE=""
PYTHON_BIN="${PYTHON_BIN:-python3}"

summary() { printf '%s\n' "$1"; }

fail_short() {
  summary "FAILED: $1"
  if [ -n "$LOG_FILE" ]; then summary "Log: $LOG_FILE"; fi
  exit 1
}

ensure_git_identity() {
  name="$(git config user.name 2>/dev/null)"
  email="$(git config user.email 2>/dev/null)"
  if [ -z "$name" ]; then git config user.name "oris-runtime-bot" >> "$LOG_FILE" 2>&1; fi
  if [ -z "$email" ]; then git config user.email "oris-runtime-bot@example.local" >> "$LOG_FILE" 2>&1; fi
}

commit_and_push_evidence() {
  status_label="$1"
  commit_message="$2"

  cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo for evidence commit"
  ensure_git_identity

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
    summary "$status_label. No file changes to commit."
    summary "Log: $LOG_FILE"
    return 0
  fi

  git commit -m "$commit_message" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    summary "$status_label, but git commit failed."
    summary "Log: $LOG_FILE"
    return "$rc"
  fi

  evidence_sha="$(git rev-parse HEAD 2>> "$LOG_FILE")"
  "$PYTHON_BIN" - <<PY >> "$LOG_FILE" 2>&1
from pathlib import Path
p = Path("reports/execution/module_A_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
p.write_text(text, encoding="utf-8")
PY

  git add reports/execution/module_A_execution_report.md reports/execution/module_A_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-a): record evidence commit sha" >> "$LOG_FILE" 2>&1
  fi

  final_sha="$(git rev-parse HEAD 2>> "$LOG_FILE")"
  git push origin "$BRANCH" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    summary "$status_label, local evidence committed but push failed."
    summary "Local commit: $final_sha"
    summary "Log: $LOG_FILE"
    return "$rc"
  fi

  summary "$status_label. Evidence pushed."
  summary "Commit: $final_sha"
  summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_A_execution_report.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module A official bootstrap $VERSION starting..."

TEMP_LOG="/tmp/oris_module_A_bootstrap_$$.log"
LOG_FILE="$TEMP_LOG"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail_short "python3/python not found"
fi

if [ ! -d "$ORIS_DIR/.git" ]; then
  git clone "$ORIS_REPO_URL" "$ORIS_DIR" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then fail_short "cannot clone ORIS repo"; fi
else
  cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo"
  git fetch origin >> "$LOG_FILE" 2>&1
  git checkout "$BRANCH" >> "$LOG_FILE" 2>&1
  git pull --ff-only origin "$BRANCH" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then fail_short "cannot fast-forward ORIS repo; please inspect local changes in $ORIS_DIR"; fi
fi

cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo after clone/update"
mkdir -p reports/execution
LOG_FILE="$ORIS_DIR/reports/execution/module_A_bootstrap_latest.log"
{
  echo "# Module A bootstrap log"
  echo "version=$VERSION"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "oris_dir=$ORIS_DIR"
  echo "branch=$BRANCH"
  echo "python_bin=$PYTHON_BIN"
  echo ""
  echo "# pre-log bootstrap output"
  if [ -f "$TEMP_LOG" ]; then cat "$TEMP_LOG"; fi
} > "$LOG_FILE" 2>&1
rm -f "$TEMP_LOG"

summary "Checking product repo state via git ls-remote..."
PRODUCT_CHECK_STATUS="ls_remote_unknown"
PRODUCT_HEAD="$(git ls-remote "$PRODUCT_REPO_URL" "refs/heads/$BRANCH" 2>> "$LOG_FILE" | awk '{print $1}')"
if [ -n "$PRODUCT_HEAD" ]; then
  PRODUCT_CHECK_STATUS="ls_remote_ok"
else
  PRODUCT_HEAD="UNKNOWN"
  PRODUCT_CHECK_STATUS="ls_remote_failed_non_blocking"
fi

BASE_SHA="$(git rev-parse HEAD 2>> "$LOG_FILE")"
{
  echo ""
  echo "# repository state"
  echo "base_sha=$BASE_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
  if [ "$PRODUCT_HEAD" = "$MODULE0_SHA" ]; then
    echo "product_module_state=module_0_only"
  elif [ "$PRODUCT_HEAD" = "UNKNOWN" ]; then
    echo "product_module_state=unknown_non_blocking"
  else
    echo "product_module_state=has_commits_after_or_different_from_module_0"
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
  if [ -f "$f" ]; then echo "OK $f" >> "$LOG_FILE"; else echo "MISSING $f" >> "$LOG_FILE"; fi
done

mkdir -p docs/runtime_v2 schemas/runtime_v2 tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_A_TEST_PLAN.md <<'EOF'
# Module A Test Plan - Runtime v2 Architecture and State Machine

## Scope

Validate Runtime v2 Module A architecture and state machine design using Python standard-library `unittest`, avoiding external test package dependency.

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
import unittest
from pathlib import Path

SCHEMA_PATH = Path("schemas/runtime_v2/state_machine.schema.json")


class StateMachineTransitionTests(unittest.TestCase):
    def load_schema(self):
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_exists_and_has_required_keys(self):
        schema = self.load_schema()
        self.assertIn("states", schema)
        self.assertIn("terminal_states", schema)
        self.assertIn("transitions", schema)

    def test_required_states_exist(self):
        schema = self.load_schema()
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
        self.assertTrue(required.issubset(states))

    def test_required_transitions_exist(self):
        schema = self.load_schema()
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
        self.assertTrue(required.issubset(transitions))

    def test_terminal_states_have_no_outgoing_transitions(self):
        schema = self.load_schema()
        terminal_states = set(schema["terminal_states"])
        transitions = {tuple(item) for item in schema["transitions"]}
        outgoing_from_terminal = [
            transition for transition in transitions if transition[0] in terminal_states
        ]
        self.assertEqual(outgoing_from_terminal, [])

    def test_every_transition_uses_declared_states(self):
        schema = self.load_schema()
        states = set(schema["states"])
        for source, target in schema["transitions"]:
            self.assertIn(source, states)
            self.assertIn(target, states)


if __name__ == "__main__":
    unittest.main()
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

summary "Generated Module A files. Running stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA LOG_FILE PRODUCT_CHECK_STATUS TEST_COMMAND VERSION
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path

result = {
    "module": "Runtime v2 Module A",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": [
        "schema_exists",
        "required_states_exist",
        "required_transitions_exist",
        "terminal_states_have_no_outgoing_transitions",
        "every_transition_uses_declared_states",
    ],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_A_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_A_execution_report.md <<EOF
# Runtime v2 Module A Execution Report

## Module

Architecture and State Machine Design

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Product Repository Check

- Product repo check status: $PRODUCT_CHECK_STATUS
- Product repo head: $PRODUCT_HEAD
- Module 0 expected commit: $MODULE0_SHA
- Old interactive insight product continued: no

## Test Command

\`$TEST_COMMAND\`

## Test Result

- test exit code: $TEST_RC
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

## Module A Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_A_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module A tests passed" "runtime-v2(module-a): add architecture and state machine design"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module A tests failed" "runtime-v2(module-a): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
