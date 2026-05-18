#!/usr/bin/env python3
"""Smoke test for Dev Employee execution packet builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.execution_packet import build_execution_packet, write_execution_packet


def main() -> int:
    output_dir = Path("run/dev_employee/execution_packet_smoke")
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = build_execution_packet(output_dir=output_dir)
    write_execution_packet(output_dir, packet)
    payload = packet.to_dict()
    ok = bool(payload.get("ok")) and payload.get("approved_for_real_execution") is False
    print(json.dumps({"ok": ok, "packet_ok": payload.get("ok"), "codex_prompt_path": payload.get("codex_prompt_path")}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
