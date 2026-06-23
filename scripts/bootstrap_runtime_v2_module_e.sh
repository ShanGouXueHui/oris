#!/usr/bin/env bash

# ORIS Runtime v2 Module E official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-23-runtime-v2-module-e-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_E_COMMIT_AND_PUSH:-1}"
MODULE_D_FINAL_SHA="62506edf6ef6fa439a8992e904a5d2bc510a26f1"
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
    docs/runtime_v2/GITHUB_EVIDENCE_PUBLISHER_AND_RUN_EVIDENCE_INDEX_MODULE_E.md \
    schemas/runtime_v2/evidence_index.schema.json \
    schemas/runtime_v2/github_publish_plan.schema.json \
    scripts/lib/runtime_v2_evidence_publisher.py \
    tests/runtime_v2/test_evidence_publisher.py \
    docs/testing/MODULE_E_TEST_PLAN.md \
    reports/testing/module_E_test_result.json \
    reports/testing/latest_test_result.json \
    reports/execution/module_E_execution_report.md \
    reports/execution/module_E_bootstrap_latest.log >> "$LOG_FILE" 2>&1

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
p = Path("reports/execution/module_E_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
p.write_text(text, encoding="utf-8")
PY

  git add reports/execution/module_E_execution_report.md reports/execution/module_E_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-e): record evidence commit sha" >> "$LOG_FILE" 2>&1
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
  summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_E_execution_report.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module E official bootstrap $VERSION starting..."

TEMP_LOG="/tmp/oris_module_E_bootstrap_$$.log"
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
LOG_FILE="$ORIS_DIR/reports/execution/module_E_bootstrap_latest.log"
{
  echo "# Module E bootstrap log"
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

DUPLICATE_BOOTSTRAPS="$(find scripts -maxdepth 1 -type f -name 'bootstrap_runtime_v2_module_e*.sh' ! -name 'bootstrap_runtime_v2_module_e.sh' -print 2>> "$LOG_FILE")"
if [ -n "$DUPLICATE_BOOTSTRAPS" ]; then
  echo "duplicate_module_e_bootstraps=$DUPLICATE_BOOTSTRAPS" >> "$LOG_FILE"
  fail_short "duplicate Module E bootstrap entrypoints found; keep one official entry only"
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
  echo "module_D_expected_final_sha=$MODULE_D_FINAL_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
  echo ""
  echo "# module D evidence check"
  if [ -f reports/testing/latest_test_result.json ]; then cat reports/testing/latest_test_result.json; else echo "missing reports/testing/latest_test_result.json"; fi
} >> "$LOG_FILE" 2>&1

mkdir -p docs/runtime_v2 schemas/runtime_v2 scripts/lib tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_E_TEST_PLAN.md <<'EOF'
# Module E Test Plan - GitHub Evidence Publisher and Run Evidence Index

## Scope

Validate deterministic evidence aggregation and publish-plan generation so ORIS progress can be audited from GitHub without relying on chat history or long terminal logs.

## Test Targets

1. Evidence artifacts are hashed and captured in an evidence index.
2. Missing artifacts are rejected before publishing.
3. Evidence index IDs are deterministic for the same module and artifact set.
4. Publish plans include branch, commit message, files, and evidence index reference.
5. GitHub issue update payloads summarize module status and evidence paths.
6. Executor/worker evidence artifacts can be aggregated into the index.

## Acceptance

Module E passes only when tests pass and evidence is written to:

- `reports/testing/module_E_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_E_execution_report.md`
EOF

cat > schemas/runtime_v2/evidence_index.schema.json <<'EOF'
{
  "version": "runtime_v2_module_E",
  "type": "object",
  "required": ["index_id", "module", "status", "artifacts", "created_at"],
  "properties": {
    "index_id": {"type": "string"},
    "module": {"type": "string"},
    "status": {"type": "string"},
    "artifacts": {"type": "array"},
    "created_at": {"type": "string"},
    "commit_sha": {"type": ["string", "null"]}
  }
}
EOF

cat > schemas/runtime_v2/github_publish_plan.schema.json <<'EOF'
{
  "version": "runtime_v2_module_E",
  "type": "object",
  "required": ["branch", "commit_message", "files", "evidence_index_ref"],
  "properties": {
    "branch": {"type": "string"},
    "commit_message": {"type": "string"},
    "files": {"type": "array", "items": {"type": "string"}},
    "evidence_index_ref": {"type": "string"},
    "issue_update": {"type": "object"}
  }
}
EOF

cat > scripts/lib/runtime_v2_evidence_publisher.py <<'EOF'
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from runtime_v2_run_store import utc_now


class EvidencePublisherError(Exception):
    pass


class MissingEvidenceError(EvidencePublisherError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_index_id(module: str, artifacts: List[Dict[str, Any]]) -> str:
    stable = {
        "module": module,
        "artifacts": [
            {"path": artifact["path"], "sha256": artifact["sha256"], "size_bytes": artifact["size_bytes"]}
            for artifact in artifacts
        ],
    }
    raw = json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


class RuntimeV2EvidencePublisher:
    def __init__(self, repo_root: Path | str = ".") -> None:
        self.repo_root = Path(repo_root)

    def collect_artifacts(self, paths: Iterable[str]) -> List[Dict[str, Any]]:
        artifacts: List[Dict[str, Any]] = []
        for raw_path in sorted(paths):
            path = self.repo_root / raw_path
            if not path.exists() or not path.is_file():
                raise MissingEvidenceError(f"missing evidence artifact: {raw_path}")
            artifacts.append({
                "path": raw_path,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            })
        return artifacts

    def build_index(self, module: str, status: str, artifact_paths: Iterable[str], commit_sha: Optional[str] = None) -> Dict[str, Any]:
        artifacts = self.collect_artifacts(artifact_paths)
        return {
            "index_id": deterministic_index_id(module, artifacts),
            "module": module,
            "status": status,
            "artifacts": artifacts,
            "created_at": utc_now(),
            "commit_sha": commit_sha,
        }

    def write_index(self, index: Dict[str, Any], output_path: str) -> str:
        path = self.repo_root / output_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return output_path

    def create_publish_plan(self, branch: str, commit_message: str, files: Iterable[str], evidence_index_ref: str, issue_number: Optional[int] = None) -> Dict[str, Any]:
        file_list = sorted(files)
        issue_update = self.create_issue_update_payload(issue_number, commit_message, evidence_index_ref) if issue_number is not None else {}
        return {
            "branch": branch,
            "commit_message": commit_message,
            "files": file_list,
            "evidence_index_ref": evidence_index_ref,
            "issue_update": issue_update,
        }

    def create_issue_update_payload(self, issue_number: Optional[int], summary: str, evidence_index_ref: str) -> Dict[str, Any]:
        return {
            "issue_number": issue_number,
            "summary": summary,
            "evidence_index_ref": evidence_index_ref,
            "body": f"Runtime v2 evidence updated: {summary}\n\nEvidence index: `{evidence_index_ref}`",
        }
EOF

cat > tests/runtime_v2/test_evidence_publisher.py <<'EOF'
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))

from runtime_v2_evidence_publisher import MissingEvidenceError, RuntimeV2EvidencePublisher
from runtime_v2_executor import RuntimeV2Executor
from runtime_v2_run_store import RuntimeV2RunStore
from runtime_v2_worker import RuntimeV2Worker


class RuntimeV2EvidencePublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "reports/testing").mkdir(parents=True)
        (self.root / "reports/testing/a.json").write_text('{"status":"passed"}', encoding="utf-8")
        (self.root / "reports/execution").mkdir(parents=True)
        (self.root / "reports/execution/a.md").write_text('# ok', encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_artifact_hash_capture(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        index = publisher.build_index("Module E", "passed", ["reports/testing/a.json", "reports/execution/a.md"])
        self.assertEqual(index["module"], "Module E")
        self.assertEqual(len(index["artifacts"]), 2)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in index["artifacts"]))

    def test_missing_artifact_protection(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        with self.assertRaises(MissingEvidenceError):
            publisher.build_index("Module E", "failed", ["missing.txt"])

    def test_deterministic_index_id(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        first = publisher.build_index("Module E", "passed", ["reports/testing/a.json", "reports/execution/a.md"])
        second = publisher.build_index("Module E", "passed", ["reports/execution/a.md", "reports/testing/a.json"])
        self.assertEqual(first["index_id"], second["index_id"])

    def test_publish_plan_generation(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        plan = publisher.create_publish_plan("main", "runtime-v2(module-e): evidence", ["b", "a"], "reports/evidence/index.json", issue_number=15)
        self.assertEqual(plan["branch"], "main")
        self.assertEqual(plan["files"], ["a", "b"])
        self.assertEqual(plan["issue_update"]["issue_number"], 15)

    def test_issue_payload_generation(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        payload = publisher.create_issue_update_payload(15, "Module E passed", "reports/evidence/index.json")
        self.assertIn("Module E passed", payload["body"])
        self.assertIn("reports/evidence/index.json", payload["body"])

    def test_executor_worker_evidence_aggregation(self):
        evidence_dir = self.root / "executor_evidence"
        executor = RuntimeV2Executor(evidence_dir)
        store = RuntimeV2RunStore(self.root / "runtime_store.json")
        worker = RuntimeV2Worker(store, "worker-e")
        run = store.create_run("module e aggregation", "Module E")
        store.enqueue(run["run_id"])
        worker.run_once(executor.as_worker_executor({"action_type": "write_evidence", "payload": {"note": "ok"}, "risk_level": "LOW"}))
        artifact_paths = [str(path.relative_to(self.root)) for path in evidence_dir.glob("*.json")]
        self.assertEqual(len(artifact_paths), 1)
        publisher = RuntimeV2EvidencePublisher(self.root)
        index = publisher.build_index("Module E", "passed", artifact_paths)
        self.assertEqual(len(index["artifacts"]), 1)


if __name__ == "__main__":
    unittest.main()
EOF

cat > docs/runtime_v2/GITHUB_EVIDENCE_PUBLISHER_AND_RUN_EVIDENCE_INDEX_MODULE_E.md <<'EOF'
# Runtime v2 Module E - GitHub Evidence Publisher and Run Evidence Index

## Objective

Module E makes ORIS runtime progress auditable from GitHub by generating deterministic evidence indexes and publish plans.

## Evidence Index Contract

An evidence index aggregates module artifacts and records:

- module name;
- status;
- artifact path;
- artifact SHA-256;
- artifact size;
- optional commit SHA.

The schema is stored in `schemas/runtime_v2/evidence_index.schema.json`.

## Publish Plan Contract

A publish plan records:

- target branch;
- commit message;
- files to publish;
- evidence index reference;
- optional issue update payload.

The schema is stored in `schemas/runtime_v2/github_publish_plan.schema.json`.

## Determinism

The evidence index id is derived from module name and artifact hashes. It is stable for the same artifact set even when input order changes.

## GitHub Boundary

Module E does not directly call GitHub APIs. It prepares auditable local contracts that ORIS or a GitHub connector can apply later. This keeps the runtime substrate testable without credentials.

## Non-Goals

- No credential handling.
- No direct GitHub API mutation.
- No product repository mutation.
- No deployment workflow.
EOF

summary "Generated Module E files. Running stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA PRODUCT_CHECK_STATUS TEST_COMMAND VERSION MODULE_D_FINAL_SHA LOG_FILE
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path

result = {
    "module": "Runtime v2 Module E",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "module_D_final_sha": os.environ.get("MODULE_D_FINAL_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": [
        "artifact_hash_capture",
        "missing_artifact_protection",
        "deterministic_index_id",
        "publish_plan_generation",
        "issue_payload_generation",
        "executor_worker_evidence_aggregation",
    ],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_E_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_E_execution_report.md <<EOF
# Runtime v2 Module E Execution Report

## Module

GitHub Evidence Publisher and Run Evidence Index

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Module D Baseline

$MODULE_D_FINAL_SHA

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

- \`docs/runtime_v2/GITHUB_EVIDENCE_PUBLISHER_AND_RUN_EVIDENCE_INDEX_MODULE_E.md\`
- \`schemas/runtime_v2/evidence_index.schema.json\`
- \`schemas/runtime_v2/github_publish_plan.schema.json\`
- \`scripts/lib/runtime_v2_evidence_publisher.py\`
- \`tests/runtime_v2/test_evidence_publisher.py\`
- \`docs/testing/MODULE_E_TEST_PLAN.md\`
- \`reports/testing/module_E_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_E_bootstrap_latest.log\`

## Module E Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_E_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module E tests passed" "runtime-v2(module-e): add github evidence publisher and index"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module E tests failed" "runtime-v2(module-e): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
