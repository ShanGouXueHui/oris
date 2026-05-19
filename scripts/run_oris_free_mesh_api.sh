#!/usr/bin/env bash

ROOT_DIR="${ORIS_REPO_DIR:-$HOME/projects/oris}"
cd "$ROOT_DIR" || exit 1

exec /usr/bin/python3 scripts/oris_free_mesh_api.py
