#!/usr/bin/env bash

# ORIS Runtime v2 Module H official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-23-runtime-v2-module-h-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_H_COMMIT_AND_PUSH:-1}"
MODULE_G_FINAL_SHA="2a9b105ef0a11578db961d7e78a94f1166bdab84"
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
    docs/runtime_v2/FINAL_ACCEPTANCE_AND_INSIGHT_REBUILD_HANDOFF_MODULE_H.md \
    docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md \
    memory/dev_employee/NEXT_CHAT_START_PROMPT_2026-06-23_INSIGHT_REBUILD_AFTER_RUNTIME_V2.md \
    tests/runtime_v2/test_final_acceptance_gate.py \
    docs/testing/MODULE_H_TEST_PLAN.md \
    reports/testing/module_H_test_result.json \
    reports/testing/latest_test_result.json \
    reports/execution/module_H_execution_report.md \
    reports/execution/module_H_bootstrap_latest.log >> "$LOG_FILE" 2>&1
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
for raw in ["reports/execution/module_H_execution_report.md", "docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md"]:
    p = Path(raw)
    text = p.read_text(encoding="utf-8")
    text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
    p.write_text(text, encoding="utf-8")
PY
  git add reports/execution/module_H_execution_report.md docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md reports/execution/module_H_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-h): record final acceptance evidence sha" >> "$LOG_FILE" 2>&1
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
  summary "Evidence: reports/testing/latest_test_result.json; docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module H official bootstrap $VERSION starting..."
TEMP_LOG="/tmp/oris_module_H_bootstrap_$$.log"
LOG_FILE="$TEMP_LOG"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then PYTHON_BIN="python"; fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then fail_short "python3/python not found"; fi

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
  if [ "$rc" -ne 0 ]; then fail_short "cannot fast-forward ORIS repo; inspect local changes in $ORIS_DIR"; fi
fi

cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo after clone/update"
mkdir -p reports/execution
LOG_FILE="$ORIS_DIR/reports/execution/module_H_bootstrap_latest.log"
{
  echo "# Module H bootstrap log"
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

DUPLICATE_BOOTSTRAPS="$(find scripts -maxdepth 1 -type f -name 'bootstrap_runtime_v2_module_h*.sh' ! -name 'bootstrap_runtime_v2_module_h.sh' -print 2>> "$LOG_FILE")"
if [ -n "$DUPLICATE_BOOTSTRAPS" ]; then
  echo "duplicate_module_h_bootstraps=$DUPLICATE_BOOTSTRAPS" >> "$LOG_FILE"
  fail_short "duplicate Module H bootstrap entrypoints found; keep one official entry only"
fi

summary "Checking product repo state via git ls-remote..."
PRODUCT_CHECK_STATUS="ls_remote_unknown"
PRODUCT_HEAD="$(git ls-remote "$PRODUCT_REPO_URL" "refs/heads/$BRANCH" 2>> "$LOG_FILE" | awk '{print $1}')"
if [ -n "$PRODUCT_HEAD" ]; then PRODUCT_CHECK_STATUS="ls_remote_ok"; else PRODUCT_HEAD="UNKNOWN"; PRODUCT_CHECK_STATUS="ls_remote_failed_non_blocking"; fi
BASE_SHA="$(git rev-parse HEAD 2>> "$LOG_FILE")"
{
  echo ""
  echo "# repository state"
  echo "base_sha=$BASE_SHA"
  echo "module_G_expected_final_sha=$MODULE_G_FINAL_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
} >> "$LOG_FILE" 2>&1

mkdir -p docs/runtime_v2 tests/runtime_v2 docs/testing reports/testing reports/execution memory/dev_employee

cat > docs/testing/MODULE_H_TEST_PLAN.md <<'EOF'
# Module H Test Plan - Final Acceptance Gate and Insight Rebuild Handoff

## Scope

Validate Runtime v2 final acceptance evidence and create the handoff for rebuilding insight capability with the upgraded runtime.

## Test Targets

1. Module A-G evidence reports exist.
2. Latest test result references Module G before Module H execution.
3. Core runtime library files exist.
4. All runtime_v2 unittest suites pass.
5. Final acceptance report is generated.
6. Insight rebuild handoff prompt is generated.

## Acceptance

Module H passes only when tests pass and evidence is written to:

- `reports/testing/module_H_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_H_execution_report.md`
- `docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md`
EOF

cat > tests/runtime_v2/test_final_acceptance_gate.py <<'EOF'
import json
import unittest
from pathlib import Path


class RuntimeV2FinalAcceptanceGateTests(unittest.TestCase):
    def test_module_a_to_g_execution_reports_exist(self):
        for module in "ABCDEFG":
            self.assertTrue(Path(f"reports/execution/module_{module}_execution_report.md").exists(), module)

    def test_runtime_core_files_exist(self):
        expected = [
            "scripts/lib/runtime_v2_run_store.py",
            "scripts/lib/runtime_v2_worker.py",
            "scripts/lib/runtime_v2_executor.py",
            "scripts/lib/runtime_v2_evidence_publisher.py",
            "scripts/lib/runtime_v2_approval_gate.py",
            "scripts/lib/runtime_v2_acceptance_harness.py",
        ]
        for path in expected:
            self.assertTrue(Path(path).exists(), path)

    def test_module_g_latest_result_was_passed_before_final_gate(self):
        data = json.loads(Path("reports/testing/latest_test_result.json").read_text(encoding="utf-8"))
        self.assertEqual(data.get("module"), "Runtime v2 Module G")
        self.assertEqual(data.get("status"), "passed")
        self.assertEqual(data.get("test_exit_code"), 0)

    def test_no_product_repo_mutation_declared(self):
        data = json.loads(Path("reports/testing/latest_test_result.json").read_text(encoding="utf-8"))
        self.assertFalse(data.get("old_interactive_insight_product_continued"))


if __name__ == "__main__":
    unittest.main()
EOF

summary "Generated Module H files. Running full runtime_v2 stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

cat > docs/runtime_v2/FINAL_ACCEPTANCE_AND_INSIGHT_REBUILD_HANDOFF_MODULE_H.md <<'EOF'
# Runtime v2 Module H - Final Acceptance and Insight Rebuild Handoff

## Objective

Module H finalizes Runtime v2 acceptance by verifying A-G evidence and generating the next-stage handoff for rebuilding the commercial insight employee using the upgraded ORIS runtime.

## Boundary

Module H is still an ORIS platform module. It does not modify the product repository.
EOF

cat > docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md <<EOF
# ORIS Autonomous Dev Employee Runtime v2 Final Acceptance Report

## Status

$TEST_STATUS

## Final Gate Test Command

\`$TEST_COMMAND\`

## Final Gate Test Exit Code

$TEST_RC

## Accepted Modules

- Module A: Architecture and State Machine Design
- Module B: Persistent Run Store and Queue Contract
- Module C: Autonomous Worker Loop and Repair Policy
- Module D: Tool Executor Adapter and Evidence Contract
- Module E: GitHub Evidence Publisher and Run Evidence Index
- Module F: Approval Gate and Control Plane Contract
- Module G: End-to-End Runtime Harness and Acceptance Runner
- Module H: Final Acceptance Gate and Insight Rebuild Handoff

## Product Repository Check

- Product repo check status: $PRODUCT_CHECK_STATUS
- Product repo head: $PRODUCT_HEAD
- Module 0 expected commit: $MODULE0_SHA
- Product repo mutation during runtime acceptance: no

## Runtime v2 Final Evidence Commit SHA

Pending until evidence commit completes.

## Next Phase

Rebuild the commercial insight capability using the upgraded Runtime v2 substrate. The product repository remains `ShanGouXueHui/oris-commercial-insight-employee`.
EOF

cat > memory/dev_employee/NEXT_CHAT_START_PROMPT_2026-06-23_INSIGHT_REBUILD_AFTER_RUNTIME_V2.md <<'EOF'
Continue ORIS / OpenClaw / Codex-backed AI Dev Employee after Runtime v2 final acceptance.

Do not rebuild from scratch. First read GitHub evidence from `ShanGouXueHui/oris`:

1. `docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md`
2. `reports/testing/latest_test_result.json`
3. `reports/execution/module_H_execution_report.md`
4. `memory/dev_employee/ENGINEERING_GUARDRAILS_SCRIPT_AND_EVIDENCE_2026-06-22.md`
5. `memory/dev_employee/GUARDRAIL_MINIMAL_MANUAL_INTERVENTION_2026-06-23.md`

Then inspect product repo `ShanGouXueHui/oris-commercial-insight-employee`.

Goal: rebuild commercial insight capability using Runtime v2 as the autonomous development employee substrate. Do not continue old interactive insight product blindly. Start with a fresh evidence-backed module plan for insight rebuild.
EOF

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA PRODUCT_CHECK_STATUS TEST_COMMAND VERSION MODULE_G_FINAL_SHA LOG_FILE
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path
result = {
    "module": "Runtime v2 Module H",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "module_G_final_sha": os.environ.get("MODULE_G_FINAL_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": ["module_a_to_g_reports_exist", "runtime_core_files_exist", "full_runtime_v2_unittest", "final_acceptance_report", "insight_rebuild_handoff"],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_H_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_H_execution_report.md <<EOF
# Runtime v2 Module H Execution Report

## Module

Final Acceptance Gate and Insight Rebuild Handoff

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Module G Baseline

$MODULE_G_FINAL_SHA

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

- \`docs/runtime_v2/FINAL_ACCEPTANCE_AND_INSIGHT_REBUILD_HANDOFF_MODULE_H.md\`
- \`docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md\`
- \`memory/dev_employee/NEXT_CHAT_START_PROMPT_2026-06-23_INSIGHT_REBUILD_AFTER_RUNTIME_V2.md\`
- \`tests/runtime_v2/test_final_acceptance_gate.py\`
- \`docs/testing/MODULE_H_TEST_PLAN.md\`
- \`reports/testing/module_H_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_H_bootstrap_latest.log\`

## Module H Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_H_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module H tests passed" "runtime-v2(module-h): add final acceptance gate and insight rebuild handoff"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module H tests failed" "runtime-v2(module-h): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
