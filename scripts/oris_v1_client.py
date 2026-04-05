#!/usr/bin/env python3
import argparse
import base64
import json
import urllib.request

def post_json(url: str, payload: dict, basic_user: str, basic_pass: str, api_key: str, timeout: int = 120):
    basic = base64.b64encode(f"{basic_user}:{basic_pass}".encode("utf-8")).decode("utf-8")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {basic}",
            "X-ORIS-API-Key": api_key,
            "User-Agent": "ORIS-V1-Client/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://control.orisfy.com/oris-api")
    ap.add_argument("--basic-user", required=True)
    ap.add_argument("--basic-pass", required=True)
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--role", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--source", default="external_client")
    ap.add_argument("--request-id", default=None)
    args = ap.parse_args()

    payload = {
        "role": args.role,
        "prompt": args.prompt,
        "source": args.source,
    }
    if args.request_id:
        payload["request_id"] = args.request_id

    url = args.base_url.rstrip("/") + "/v1/infer"
    result = post_json(
        url=url,
        payload=payload,
        basic_user=args.basic_user,
        basic_pass=args.basic_pass,
        api_key=args.api_key,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
