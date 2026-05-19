#!/usr/bin/env python3
"""Safely inspect OpenClaw model configuration without printing secrets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"

SECRET_WORDS = ("key", "token", "secret", "password", "credential")


def mask(value: Any, key: str = "") -> Any:
    if any(word in key.lower() for word in SECRET_WORDS):
        if value is None:
            return None
        return "***MASKED***"
    if isinstance(value, dict):
        return {k: mask(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [mask(v, key) for v in value]
    return value


def find_model_refs(obj: Any, path: str = "$", out: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if k in {"model", "models", "provider", "providers", "primary", "baseURL", "baseUrl", "apiBase", "api_base"}:
                out.append({"path": p, "value": mask(v, k)})
            find_model_refs(v, p, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_model_refs(v, f"{path}[{i}]", out)
    return out


def main() -> int:
    if not CONFIG_PATH.exists():
        print(json.dumps({"ok": False, "error": "openclaw_config_not_found", "path": str(CONFIG_PATH)}, ensure_ascii=False))
        return 1
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    refs = find_model_refs(data)
    openrouter_hits = []
    free_mesh_hits = []
    for item in refs:
        text = json.dumps(item.get("value"), ensure_ascii=False)
        if "openrouter/auto" in text or "openrouter" in text:
            openrouter_hits.append(item)
        if "oris/free" in text or "127.0.0.1:8789" in text:
            free_mesh_hits.append(item)
    print(json.dumps({
        "ok": True,
        "path": str(CONFIG_PATH),
        "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else [],
        "openrouter_ref_count": len(openrouter_hits),
        "free_mesh_ref_count": len(free_mesh_hits),
        "openrouter_refs": openrouter_hits[:20],
        "free_mesh_refs": free_mesh_hits[:20],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
