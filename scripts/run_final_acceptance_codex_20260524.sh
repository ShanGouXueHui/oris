#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
PROJECTS_DIR="/home/admin/projects"
PROMPT_FILE="$ORIS_DIR/prompts/dev_employee_final_acceptance_api_20260524.md"
CODEX_BIN="/home/admin/.npm-global/bin/codex"
RUN_LOG="$ORIS_DIR/logs/dev_employee/final_acceptance_codex_run_20260524.log"

mkdir -p "$ORIS_DIR/logs/dev_employee"

{
  echo "===== environment ====="
  date -Iseconds
  whoami
  pwd
  echo "HOME=$HOME"
  echo

  echo "===== oris repo ====="
  cd "$ORIS_DIR" || exit 1
  git status --short
  git log -1 --oneline
  echo

  echo "===== prompt check ====="
  if [ ! -f "$PROMPT_FILE" ]; then
    echo "MISSING_PROMPT: $PROMPT_FILE"
    exit 2
  fi
  wc -l "$PROMPT_FILE"
  echo

  echo "===== codex check ====="
  "$CODEX_BIN" --version
  gh auth status 2>&1 | head -n 60
  echo

  echo "===== run codex final acceptance ====="
  cd "$PROJECTS_DIR" || exit 1
  "$CODEX_BIN" exec --skip-git-repo-check \
    --sandbox workspace-write \
    --add-dir "$ORIS_DIR" \
    "$(cat "$PROMPT_FILE")"

  echo
  echo "===== product repo result ====="
  cd "$PROJECTS_DIR/oris-final-acceptance-api" || exit 3
  git status --short
  git log -1 --oneline

  echo
  echo "===== oris repo result ====="
  cd "$ORIS_DIR" || exit 1
  git status --short
  git log -1 --oneline
} 2>&1 | tee "$RUN_LOG"
