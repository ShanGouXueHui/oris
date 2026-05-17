#!/usr/bin/env python3
"""Smoke test for Dev Employee planning packet builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.planning_packet import build_planning_packet, write_packet_json, write_packet_markdown


def main() -> int:
    output_dir = Path("run/dev_employee/planning_packet_smoke")
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = build_planning_packet(
        repo_root=".",
        task_summary="Planning packet smoke",
        objective="Validate planning packet builder.",
    )
    json_out = output_dir / "planning_packet.json"
    md_out = output_dir / "planning_packet.md"
    write_packet_json(json_out, packet)
    write_packet_markdown(md_out, packet)
    payload = packet.to_dict()
    ok = bool(payload.get("bootstrap_ok")) and "worktree" in payload
    print(json.dumps({"ok": ok, "packet_ok": payload.get("ok"), "json_out": str(json_out), "md_out": str(md_out)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
