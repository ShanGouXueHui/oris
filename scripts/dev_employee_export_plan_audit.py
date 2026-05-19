#!/usr/bin/env python3
"""Export latest Dev Employee plan audit packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.plan_audit import build_plan_audit_packet, write_audit_json, write_audit_markdown


def main() -> int:
    packet = build_plan_audit_packet()
    json_out = Path("logs/dev_employee/latest_plan_audit.json")
    md_out = Path("logs/dev_employee/latest_plan_audit.md")
    write_audit_json(json_out, packet)
    write_audit_markdown(md_out, packet)
    payload = packet.to_dict()
    print(json.dumps({"ok": True, "audit_ok": payload.get("ok"), "recommendation": payload.get("recommendation"), "json_out": str(json_out), "md_out": str(md_out)}, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
