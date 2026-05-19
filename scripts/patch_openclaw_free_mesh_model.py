#!/usr/bin/env python3
"""Patch OpenClaw default model to ORIS Free Mesh logical model.

This script edits ~/.openclaw/openclaw.json only. It creates an external backup
under /tmp and prints a redacted before/after summary. It does not touch secrets.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
LOGICAL_MODEL = "oris/free-auto"
OLD_MODEL = "openrouter/auto"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def model_summary(data: dict[str, Any]) -> dict[str, Any]:
    defaults = ((data.get("agents") or {}).get("defaults") or {})
    return {
        "agents.defaults.model": defaults.get("model"),
        "agents.defaults.models_keys": sorted((defaults.get("models") or {}).keys()) if isinstance(defaults.get("models"), dict) else None,
    }


def patch_config(data: dict[str, Any]) -> dict[str, Any]:
    agents = data.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    models = defaults.setdefault("models", {})
    if not isinstance(models, dict):
        models = {}
        defaults["models"] = models

    old_entry = models.get(OLD_MODEL, {}) if isinstance(models.get(OLD_MODEL), dict) else {}
    models[LOGICAL_MODEL] = {
        "alias": "ORIS Free Mesh",
        "notes": "Logical model routed by ORIS runtime_plan free-model failover chain.",
    }
    if OLD_MODEL in models:
        models[OLD_MODEL] = {
            **old_entry,
            "disabled_note": "Replaced as default by ORIS Free Mesh logical model. Kept for rollback only.",
        }

    model = defaults.setdefault("model", {})
    if not isinstance(model, dict):
        model = {}
        defaults["model"] = model
    model["primary"] = LOGICAL_MODEL
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch OpenClaw default model to ORIS Free Mesh.")
    parser.add_argument("--apply", action="store_true", help="Apply the patch. Without this flag, print dry-run summary only.")
    args = parser.parse_args()

    if not CONFIG_PATH.exists():
        print(json.dumps({"ok": False, "error": "openclaw_config_not_found", "path": str(CONFIG_PATH)}, ensure_ascii=False, indent=2))
        return 1

    before = load_json(CONFIG_PATH)
    after = patch_config(json.loads(json.dumps(before)))
    backup_path = Path("/tmp") / f"openclaw.json.backup.{utc_stamp()}"

    result = {
        "ok": True,
        "config_path": str(CONFIG_PATH),
        "backup_path": str(backup_path),
        "apply": args.apply,
        "before": model_summary(before),
        "after": model_summary(after),
    }

    if args.apply:
        shutil.copy2(CONFIG_PATH, backup_path)
        save_json(CONFIG_PATH, after)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
