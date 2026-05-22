#!/usr/bin/env python3
"""Inspect OpenClaw effective provider files without leaking secrets."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPENCLAW = Path.home() / ".openclaw"
AGENT = OPENCLAW / "agents" / "main" / "agent"
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_effective_provider.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_effective_provider.md"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"hf_[A-Za-z0-9_\-]{12,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-.]{12,}", re.I),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask(s: str) -> str:
    out = s
    for pat in SECRET_PATTERNS:
        out = pat.sub("***MASKED***", out)
    return out


def run(cmd: str, timeout: int = 20) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {"rc": p.returncode, "stdout": mask((p.stdout or "")[-12000:]), "stderr": mask((p.stderr or "")[-4000:])}
    except subprocess.TimeoutExpired as exc:
        return {"rc": 124, "stdout": mask(str(exc.stdout or "")[-12000:]), "stderr": mask(str(exc.stderr or "")[-4000:])}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": repr(exc), "_exists": path.exists()}


def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ["key", "token", "secret", "password"]):
                out[k] = "***MASKED***" if v else v
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    if isinstance(obj, str):
        return mask(obj)
    return obj


def find_refs() -> list[dict[str, Any]]:
    refs = []
    for path in [OPENCLAW / "openclaw.json", AGENT / "models.json", AGENT / "auth-profiles.json"] + list(AGENT.glob("*.json")):
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = []
        for term in ["openrouter", "127.0.0.1:8789", "openrouter.ai", "baseUrl", "apiKey", "provider"]:
            if term in text:
                hits.append(term)
        if hits:
            refs.append({"path": str(path), "hits": hits, "content": sanitize(load_json(path))})
    return refs


def main() -> int:
    refs = find_refs()
    grep = run("grep -RInE 'openrouter|openrouter.ai|127.0.0.1:8789|baseUrl|auth-profiles|provider' ~/.openclaw/openclaw.json ~/.openclaw/agents/main/agent 2>/dev/null | head -n 300")
    logs = run("journalctl --user -u openclaw-gateway.service -n 220 --no-pager")
    status = run("openclaw gateway status --deep")

    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "refs": refs,
        "grep_masked": grep,
        "gateway_status": status,
        "gateway_logs_tail": logs,
        "diagnosis_hint": "If logs still show public OpenRouter 402 while models.json baseUrl is local, inspect auth-profiles.json and provider profile resolution."
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Effective Provider Diagnostic\n\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- refs_count: `{len(refs)}`\n"
        "- secrets: masked\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
