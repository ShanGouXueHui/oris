#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
EXPECTED_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR_REL="logs/dev_employee/product_baseline_review"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/product-baseline-review-$STAMP.json"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/product-baseline-review-$STAMP.log"
TMP_ROOT="$(mktemp -d /tmp/oris-product-baseline-review-${STAMP}-XXXXXX)"
RESULT_JSON="$TMP_ROOT/result.json"
RUN_LOG="$TMP_ROOT/run.log"
WORKTREE="$TMP_ROOT/evidence-worktree"

RESULT="FAILED"
FAILURE_CODE=""
PRODUCT_STATUS_ENTRY_COUNT="unknown"
ONLY_README_DIRTY="unknown"
README_STAGED="unknown"
README_UNSTAGED="unknown"
README_CAPABILITIES_ADDED="unknown"
README_PATCH_CLASSIFICATION="unknown"
PRODUCT_HEAD="unknown"
PRODUCT_REMOTE_MAIN="unknown"
PRODUCT_MUTATED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_PRODUCT_BASELINE_REVIEW_FAILURE"

umask 077
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() {
  printf '%s\n' "$*" >> "$RUN_LOG"
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "PRODUCT_STATUS_ENTRY_COUNT=$PRODUCT_STATUS_ENTRY_COUNT"
  echo "ONLY_README_DIRTY=$ONLY_README_DIRTY"
  echo "README_STAGED=$README_STAGED"
  echo "README_UNSTAGED=$README_UNSTAGED"
  echo "README_CAPABILITIES_ADDED=$README_CAPABILITIES_ADDED"
  echo "README_PATCH_CLASSIFICATION=$README_PATCH_CLASSIFICATION"
  echo "PRODUCT_HEAD=$PRODUCT_HEAD"
  echo "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
  echo "PRODUCT_MUTATED=$PRODUCT_MUTATED"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail_now() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  summary
  exit 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  fail_now "wrong_linux_user" "RUN_AS_ADMIN"
fi

if [ ! -d "$ORIS_REPO/.git" ] || [ ! -d "$PRODUCT_REPO/.git" ]; then
  fail_now "required_repository_missing" "RESTORE_REPOSITORY_PATHS"
fi

if ! command -v python3 >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
  fail_now "required_tool_missing" "RESTORE_REQUIRED_HOST_TOOLS"
fi

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=READ_ONLY_PRODUCT_BASELINE_REVIEW"
log "PRODUCT_REPO=$PRODUCT_REPO"
log "PRODUCT_MUTATED=NO"

python3 - "$PRODUCT_REPO" "$EXPECTED_HEAD" "$RESULT_JSON" <<'PY'
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1])
expected = sys.argv[2]
out = Path(sys.argv[3])

def run_bytes(*args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=30)
    return p.returncode, p.stdout, p.stderr

def run_text(*args):
    rc, stdout, stderr = run_bytes(*args)
    return rc, stdout.decode("utf-8", "replace").strip(), stderr.decode("utf-8", "replace").strip()

def sha256_file(path):
    p = repo / path
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

rc, raw_status, _ = run_bytes("status", "--porcelain=v1", "-z", "--untracked-files=all")
if rc != 0:
    raise SystemExit("git status failed")

parts = raw_status.split(b"\0")
entries = []
i = 0
while i < len(parts):
    item = parts[i]
    i += 1
    if not item:
        continue
    text = item.decode("utf-8", "surrogateescape")
    if len(text) < 3:
        continue
    code = text[:2]
    path = text[3:]
    original_path = None
    if code[0] in "RC" or code[1] in "RC":
        if i < len(parts) and parts[i]:
            original_path = parts[i].decode("utf-8", "surrogateescape")
            i += 1
    entries.append({
        "code": code,
        "path": path,
        "original_path": original_path,
        "staged": code[0] not in (" ", "?"),
        "unstaged": code[1] not in (" ", "?"),
        "untracked": code == "??",
        "working_tree_sha256": sha256_file(path),
    })

_, head, _ = run_text("rev-parse", "HEAD")
_, branch, _ = run_text("branch", "--show-current")
_, remote, _ = run_text("remote", "get-url", "origin")
rc_remote, remote_line, _ = run_text("ls-remote", "--heads", "origin", "refs/heads/main")
remote_main = remote_line.split()[0] if rc_remote == 0 and remote_line else ""

if "://" in remote and "@" in remote.split("://", 1)[1]:
    prefix, rest = remote.split("://", 1)
    remote = prefix + "://<redacted>@" + rest.split("@", 1)[1]

readme_entries = [e for e in entries if e["path"] == "README.md"]
only_readme_dirty = len(entries) == 1 and len(readme_entries) == 1
readme_staged = any(e["staged"] for e in readme_entries)
readme_unstaged = any(e["unstaged"] for e in readme_entries)

_, staged_diff, _ = run_text("diff", "--cached", "--unified=0", "--", "README.md")
_, unstaged_diff, _ = run_text("diff", "--unified=0", "--", "README.md")
combined = staged_diff + "\n" + unstaged_diff
added_lines = []
removed_lines = []
for line in combined.splitlines():
    if line.startswith("+++") or line.startswith("---"):
        continue
    if line.startswith("+"):
        added_lines.append(line[1:])
    elif line.startswith("-"):
        removed_lines.append(line[1:])

capabilities_added = any("/capabilities" in line for line in added_lines)
api_list_context = any(any(token in line.lower() for token in ("api", "endpoint", "接口")) for line in added_lines)

if not entries:
    classification = "clean"
elif only_readme_dirty and capabilities_added:
    classification = "known_readme_gap_candidate"
elif only_readme_dirty:
    classification = "readme_only_unknown_change"
else:
    classification = "unexpected_product_drift"

payload = {
    "task_id": "commercial-native-openclaw-ui-20260617",
    "checked_at": os.environ.get("STAMP", ""),
    "mode": "read_only_product_baseline_review",
    "safety": {
        "product_mutated": False,
        "index_mutated": False,
        "task_submitted": False,
        "diff_content_committed": False,
    },
    "repository": {
        "path": str(repo),
        "head": head,
        "branch": branch,
        "remote": remote,
        "remote_main": remote_main,
        "head_matches_expected": head == expected,
        "remote_matches_expected": remote_main == expected,
        "status_entry_count": len(entries),
        "status_entries": entries,
    },
    "readme_review": {
        "only_readme_dirty": only_readme_dirty,
        "staged": readme_staged,
        "unstaged": readme_unstaged,
        "capabilities_endpoint_added": capabilities_added,
        "api_list_context_detected": api_list_context,
        "added_line_count": len(added_lines),
        "removed_line_count": len(removed_lines),
        "staged_diff_sha256": hashlib.sha256(staged_diff.encode()).hexdigest(),
        "unstaged_diff_sha256": hashlib.sha256(unstaged_diff.encode()).hexdigest(),
        "classification": classification,
    },
    "expected_head": expected,
}
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
PY_RC="$?"
if [ "$PY_RC" -ne 0 ]; then
  fail_now "product_baseline_analysis_failed" "INSPECT_PRODUCT_REPOSITORY_READ_ONLY"
fi

python3 - "$RESULT_JSON" "$RUN_LOG" <<'PY' >> "$RUN_LOG"
import json
import sys
from pathlib import Path
p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
r = p["repository"]
m = p["readme_review"]
print(f"PRODUCT_HEAD={r['head']}")
print(f"PRODUCT_REMOTE_MAIN={r['remote_main']}")
print(f"PRODUCT_BRANCH={r['branch']}")
print(f"PRODUCT_STATUS_ENTRY_COUNT={r['status_entry_count']}")
for entry in r["status_entries"]:
    print(f"PRODUCT_STATUS code={entry['code']} path={entry['path']} staged={entry['staged']} unstaged={entry['unstaged']} untracked={entry['untracked']} sha256={entry['working_tree_sha256']}")
print(f"ONLY_README_DIRTY={'YES' if m['only_readme_dirty'] else 'NO'}")
print(f"README_STAGED={'YES' if m['staged'] else 'NO'}")
print(f"README_UNSTAGED={'YES' if m['unstaged'] else 'NO'}")
print(f"README_CAPABILITIES_ADDED={'YES' if m['capabilities_endpoint_added'] else 'NO'}")
print(f"README_API_LIST_CONTEXT={'YES' if m['api_list_context_detected'] else 'NO'}")
print(f"README_ADDED_LINE_COUNT={m['added_line_count']}")
print(f"README_REMOVED_LINE_COUNT={m['removed_line_count']}")
print(f"README_PATCH_CLASSIFICATION={m['classification']}")
PY

PRODUCT_STATUS_ENTRY_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repository"]["status_entry_count"])' "$RESULT_JSON")"
ONLY_README_DIRTY="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["readme_review"]["only_readme_dirty"] else "NO")' "$RESULT_JSON")"
README_STAGED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["readme_review"]["staged"] else "NO")' "$RESULT_JSON")"
README_UNSTAGED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["readme_review"]["unstaged"] else "NO")' "$RESULT_JSON")"
README_CAPABILITIES_ADDED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["readme_review"]["capabilities_endpoint_added"] else "NO")' "$RESULT_JSON")"
README_PATCH_CLASSIFICATION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["readme_review"]["classification"])' "$RESULT_JSON")"
PRODUCT_HEAD="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repository"]["head"])' "$RESULT_JSON")"
PRODUCT_REMOTE_MAIN="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repository"]["remote_main"])' "$RESULT_JSON")"

case "$README_PATCH_CLASSIFICATION" in
  clean)
    RESULT="DIAGNOSED"
    NEXT_ACTION="DESIGN_REVERSIBLE_NATIVE_OPENCLAW_MIGRATION"
    ;;
  known_readme_gap_candidate)
    RESULT="DIAGNOSED"
    NEXT_ACTION="PRESERVE_KNOWN_README_PATCH_AND_DESIGN_REVERSIBLE_MIGRATION"
    ;;
  readme_only_unknown_change)
    RESULT="REVIEW"
    NEXT_ACTION="INSPECT_README_CHANGE_BEFORE_MIGRATION"
    ;;
  *)
    RESULT="REVIEW"
    NEXT_ACTION="RESOLVE_UNEXPECTED_PRODUCT_DRIFT_BEFORE_MIGRATION"
    ;;
esac

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY'
import re
import sys
from pathlib import Path
patterns = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
]
for filename in sys.argv[1:]:
    text = Path(filename).read_text(encoding="utf-8", errors="replace")
    if any(p.search(text) for p in patterns):
        raise SystemExit(1)
PY
if [ "$?" -eq 0 ]; then
  SECRET_SCAN="PASS"
else
  SECRET_SCAN="FAILED"
  fail_now "evidence_secret_scan_failed" "REPAIR_BASELINE_EVIDENCE_REDACTION"
fi

if ! git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1; then
  fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
fi
if ! git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1; then
  fail_now "detached_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
fi
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY'
import json
import sys
from pathlib import Path
src_log, dst_log, src_json, dst_json = map(Path, sys.argv[1:])
lines = [line.rstrip(" \t\r") for line in src_log.read_text(encoding="utf-8", errors="replace").splitlines()]
dst_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
payload = json.loads(src_json.read_text(encoding="utf-8"))
dst_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
if [ "$?" -ne 0 ]; then
  fail_now "evidence_normalization_failed" "INSPECT_BASELINE_EVIDENCE"
fi
if ! git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL"; then
  fail_now "evidence_git_add_failed" "INSPECT_DETACHED_WORKTREE"
fi
if ! git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1; then
  fail_now "evidence_diff_check_failed" "INSPECT_BASELINE_EVIDENCE_FORMAT"
fi
if ! git -C "$WORKTREE" commit -m "chore(dev-employee): record product baseline review $STAMP" >/dev/null 2>&1; then
  fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
fi
if ! git -C "$WORKTREE" fetch origin main >/dev/null 2>&1; then
  fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
fi
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  if ! git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1; then
    fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
  fi
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
if ! git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1; then
  fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
fi
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then
  EVIDENCE_REMOTE_VERIFIED="YES"
else
  RESULT="FAILED"
  FAILURE_CODE="evidence_remote_sha_mismatch"
  NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"
fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
