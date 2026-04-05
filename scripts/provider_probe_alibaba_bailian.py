#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
CANDIDATE_MODELS = [
    "qwen3.6-plus",
    "qwen-coder-turbo-0919",
    "qwen-math-turbo",
    "qvq-max-2025-03-25",
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def deep_get(data, path):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

def load_key():
    if not SECRETS_PATH.exists():
        return None

    data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))

    candidates = [
        ["models", "providers", "alibaba_bailian", "apiKey"],
        ["models", "providers", "Alibailian", "apiKey"],
        ["models", "providers", "alibailian", "apiKey"],
        ["models", "providers", "AlibabaBailian", "apiKey"],
    ]

    for path in candidates:
        value = deep_get(data, path)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None

def try_model(key, model):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "temperature": 0
    }

    req = urllib.request.Request(
        CHAT_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ORIS-Provider-Probe/1.0"
        },
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    key = load_key()
    if not key:
        print(json.dumps({
            "provider_id": "alibaba_bailian",
            "status": "not_configured",
            "last_probe_at": utc_now(),
            "models": [],
            "error": "missing_api_key"
        }, ensure_ascii=False, indent=2))
        return

    discovered = []
    errors = []

    for model in CANDIDATE_MODELS:
        try:
            _ = try_model(key, model)
            discovered.append({"model_id": model, "free_candidate": True})
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            errors.append({"model": model, "error": f"http_{e.code}", "body": body})
        except Exception as e:
            errors.append({"model": model, "error": f"{type(e).__name__}: {e}", "body": ""})

    status = "healthy" if discovered else "degraded"
    print(json.dumps({
        "provider_id": "alibaba_bailian",
        "status": status,
        "last_probe_at": utc_now(),
        "models": discovered,
        "error": None if discovered else "no_candidate_model_succeeded",
        "errors": errors[:5]
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
