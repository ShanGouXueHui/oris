#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]

def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))

def load_env_file():
    for p in [ROOT / ".env", ROOT / "config" / ".env"]:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

def getenv_any(names):
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None

def get_token():
    load_env_file()
    app_id = getenv_any(["FEISHU_APP_ID", "LARK_APP_ID", "APP_ID"])
    app_secret = getenv_any(["FEISHU_APP_SECRET", "LARK_APP_SECRET", "APP_SECRET"])
    if not app_id or not app_secret:
        raise RuntimeError("missing FEISHU_APP_ID/FEISHU_APP_SECRET (or LARK_*)")

    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=20
    )
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"get tenant token failed: {data}")
    return data["tenant_access_token"]

def chunk_text(text, limit=3000):
    s = (text or "").strip()
    if not s:
        return []
    out = []
    while len(s) > limit:
        cut = s.rfind("\n", 0, limit)
        if cut < 500:
            cut = limit
        out.append(s[:cut].strip())
        s = s[cut:].strip()
    if s:
        out.append(s)
    return out

def send_text(chat_id, text):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    sent = []
    for part in chunk_text(text):
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": part}, ensure_ascii=False)
        }
        r = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            headers=headers,
            json=payload,
            timeout=30
        )
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"send feishu text failed: {data}")
        sent.append(data.get("data") or {})
    return sent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True)
    ap.add_argument("--text-file", required=True)
    args = ap.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8")
    sent = send_text(args.chat_id, text)

    print_json({
        "ok": True,
        "chat_id": args.chat_id,
        "message_count": len(sent)
    })

if __name__ == "__main__":
    main()
