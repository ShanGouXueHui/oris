#!/usr/bin/env python3
"""Run latency probes against ORIS Free Mesh and export compact audit logs."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE_SCRIPT = ROOT / "scripts" / "probe_oris_free_mesh_api.py"
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_free_mesh_latency_audit.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_free_mesh_latency_audit.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_probe(timeout: int) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(
        ["/usr/bin/python3", str(PROBE_SCRIPT)],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    item: dict[str, Any] = {
        "elapsed_ms": elapsed_ms,
        "rc": proc.returncode,
        "stdout_preview": (proc.stdout or "")[-1000:],
        "stderr_preview": (proc.stderr or "")[-1000:],
    }
    try:
        payload = json.loads(proc.stdout or "{}")
        item.update(
            {
                "ok": bool(payload.get("ok")),
                "text_preview": payload.get("text_preview"),
                "model": payload.get("model"),
                "used_model": (payload.get("oris") or {}).get("used_model"),
                "used_provider": (payload.get("oris") or {}).get("used_provider"),
                "routing": (payload.get("oris") or {}).get("routing"),
                "error": payload.get("error"),
                "status": payload.get("status"),
            }
        )
    except Exception as exc:
        item["ok"] = False
        item["parse_error"] = repr(exc)
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--target-ms", type=int, default=15000)
    args = parser.parse_args()

    samples = []
    for _ in range(max(1, args.samples)):
        samples.append(run_probe(args.timeout))

    latencies = [x["elapsed_ms"] for x in samples if x.get("ok")]
    p50 = round(statistics.median(latencies)) if latencies else None
    max_ms = max(latencies) if latencies else None
    providers = sorted({x.get("used_provider") for x in samples if x.get("used_provider")})
    models = sorted({x.get("used_model") for x in samples if x.get("used_model")})
    ok = bool(latencies) and all(x.get("ok") for x in samples) and (p50 or 999999) <= args.target_ms

    payload = {
        "ok": ok,
        "generated_at": utc_now(),
        "target_ms": args.target_ms,
        "sample_count": len(samples),
        "success_count": len(latencies),
        "p50_ms": p50,
        "max_ms": max_ms,
        "used_providers": providers,
        "used_models": models,
        "samples": samples,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# Free Mesh Latency Audit\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- target_ms: `{payload['target_ms']}`\n"
        f"- sample_count: `{payload['sample_count']}`\n"
        f"- success_count: `{payload['success_count']}`\n"
        f"- p50_ms: `{payload['p50_ms']}`\n"
        f"- max_ms: `{payload['max_ms']}`\n"
        f"- used_providers: `{', '.join(providers)}`\n"
        f"- used_models: `{', '.join(models)}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": ok, "json_out": str(OUT_JSON), "md_out": str(OUT_MD), "p50_ms": p50, "max_ms": max_ms}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
