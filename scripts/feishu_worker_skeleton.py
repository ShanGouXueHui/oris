#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_SCRIPT = ROOT / "scripts" / "feishu_transport_skeleton.py"
SENDER_SCRIPT = ROOT / "scripts" / "feishu_send_executor_skeleton.py"

def run_json(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "empty output")
    try:
        data = json.loads(result.stdout)
    except Exception as e:
        raise RuntimeError(f"non-json output: {e}; stdout={result.stdout[:500]}")
    if result.returncode != 0:
        raise RuntimeError(data)
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload-file", default=None)
    ap.add_argument("--payload-json", default=None)
    ap.add_argument("--execute-send", action="store_true")
    args = ap.parse_args()

    if not args.payload_file and not args.payload_json:
        raise SystemExit("either --payload-file or --payload-json is required")

    transport_cmd = ["/usr/bin/python3", str(TRANSPORT_SCRIPT)]
    if args.payload_file:
        transport_cmd += ["--payload-file", args.payload_file]
    else:
        transport_cmd += ["--payload-json", args.payload_json]

    transport_result = run_json(transport_cmd)

    mode = transport_result.get("mode")
    if mode in {"challenge", "deduped"}:
        print(json.dumps({
            "ok": True,
            "worker_mode": mode,
            "transport_result": transport_result,
            "send_result": None,
        }, ensure_ascii=False, indent=2))
        return

    sender_cmd = [
        "/usr/bin/python3",
        str(SENDER_SCRIPT),
        "--transport-preview-json",
        json.dumps(transport_result, ensure_ascii=False),
    ]
    if args.execute_send:
        sender_cmd.append("--execute")

    send_result = run_json(sender_cmd)

    print(json.dumps({
        "ok": True,
        "worker_mode": "transport_then_send",
        "transport_result": transport_result,
        "send_result": send_result,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
