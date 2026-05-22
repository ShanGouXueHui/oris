#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

CFG = Path.home() / ".openclaw" / "openclaw.json"
MODEL_KEY = "oris/free-auto"


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = Path("/tmp") / f"openclaw-default-oris-{ts}.json"
    data = json.loads(CFG.read_text(encoding="utf-8"))
    shutil.copy2(CFG, backup)

    defaults = data.setdefault("agents", {}).setdefault("defaults", {})
    defaults["models"] = {MODEL_KEY: {"alias": "ORIS Free Mesh"}}
    defaults["model"] = {"primary": MODEL_KEY}

    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "model": MODEL_KEY, "backup": str(backup)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
