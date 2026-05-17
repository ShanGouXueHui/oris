#!/usr/bin/env python3
"""Smoke test for CodexExecutor execution gate.

This test confirms that a requested non-dry-run execution stays blocked when
runtime config remains in dry-run mode. It must not invoke Codex.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.codex_executor import CodexExecutor
from oris_vnext.validation import load_runtime_config


def main() -> int:
    output_dir = Path("run/dev_employee/codex_gate_smoke")
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "prompt.md"
    prompt_path.write_text(
        "# Codex gate smoke\n\nDo not modify files. This is a gate validation prompt.\n",
        encoding="utf-8",
    )

    cfg = load_runtime_config("config/dev_employee_runtime.json")
    result = CodexExecutor(cfg).run(prompt_path, dry_run=False)
    payload = result.to_dict()
    ok = bool(payload.get("dry_run")) and payload.get("returncode") is None
    payload["ok"] = ok
    (output_dir / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
