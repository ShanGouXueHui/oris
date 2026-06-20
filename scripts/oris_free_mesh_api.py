#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from oris_vnext.free_mesh_compat import load_json
from oris_vnext.free_mesh_http import build_handler
from oris_vnext.free_mesh_inference import FreeMeshInference


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "oris_free_mesh_api.json"


def main() -> int:
    config = load_json(CONFIG_PATH)
    host = str(config.get("host", "127.0.0.1"))
    port = int(config.get("port", 8789))
    inference = FreeMeshInference(ROOT)
    if inference.warmup_enabled():
        threading.Thread(
            target=inference.warmup,
            name="oris-free-mesh-warmup",
            daemon=True,
        ).start()
    server = ThreadingHTTPServer((host, port), build_handler(ROOT))
    print(
        json.dumps(
            {
                "ok": True,
                "service": "oris-free-mesh-api",
                "protocol_version": 2,
                "tool_calling": True,
                "listen": f"http://{host}:{port}",
            },
            ensure_ascii=False,
        )
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
