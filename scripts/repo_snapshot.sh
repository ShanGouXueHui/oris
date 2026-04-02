#!/usr/bin/env bash

cd "$(dirname "$0")/.."

echo "===== pwd ====="
pwd

echo
echo "===== git remote ====="
git remote -v || true

echo
echo "===== git branch ====="
git branch --show-current || true

echo
echo "===== git status ====="
git status --short || true

echo
echo "===== recent commits ====="
git log --oneline -n 5 || true

echo
echo "===== files ====="
find . -maxdepth 2 -type f | sort
\n