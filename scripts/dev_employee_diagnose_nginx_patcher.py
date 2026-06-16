#!/usr/bin/env python3
import argparse
import importlib.util
import json
from pathlib import Path


def load_module(path):
    spec = importlib.util.spec_from_file_location("oris_nginx_patcher_diag", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patcher", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    module = load_module(Path(args.patcher))
    text = Path(args.config).read_text(encoding="utf-8")
    servers = module.directive_blocks(text, "server")
    https = []
    for item in servers:
        block = item[2]
        if "control.orisfy.com" in block and "443" in block:
            https.append(item)

    if_blocks = []
    guards = []
    chat_present = False
    if https:
        block = https[0][2]
        if_blocks = module.directive_blocks(block, "if")
        guards = [
            item
            for item in if_blocks
            if "$request_method" in item[2] and "return 403" in item[2]
        ]
        chat_present = "location = /api/chat/messages" in block

    result = {
        "server_block_count": len(servers),
        "https_match_count": len(https),
        "if_block_count": len(if_blocks),
        "method_guard_count": len(guards),
        "map_marker_present": module.MAP_MARKER in text,
        "chat_location_present": chat_present,
    }

    try:
        _, audit = module.patch_config(text)
        result.update(
            {
                "patch_result": "PASS",
                "patch_error_type": "",
                "patch_error_message": "",
                "audit": audit,
            }
        )
    except Exception as exc:
        result.update(
            {
                "patch_result": "FAILED",
                "patch_error_type": type(exc).__name__,
                "patch_error_message": str(exc)[:240],
            }
        )

    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
