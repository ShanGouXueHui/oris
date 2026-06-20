#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from oris_vnext.openai_chat_contract import (
    legacy_prompt_request,
    load_chat_request,
)
from oris_vnext.runtime_execution_engine import RuntimeExecutionEngine


ROOT = Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt")
    source.add_argument("--request-file")
    parser.add_argument("--show-raw", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    request = (
        load_chat_request(Path(args.request_file))
        if args.request_file
        else legacy_prompt_request(str(args.prompt))
    )
    output = RuntimeExecutionEngine(ROOT).execute(
        args.role,
        request,
        show_raw=args.show_raw,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
