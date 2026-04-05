#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
CHAT_URL = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions"
CANDIDATE_MODELS = [
    "hunyuan-turbos-latest",
    "hunyuan-t1-latest",
    "hunyuan-large-role-latest",
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
        ["models", "providers", "tencent_hunyuan", "apiKey"],
        ["models", "providers", "tencenthunyuan", "apiKey"],
        ["models", "providers", "Tencenthunyuan", "apiKey"],
        ["models", "providers", "tencentHunyuan", "apiKey"],
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
            "provider_id": "tencent_hunyuan",
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
        "provider_id": "tencent_hunyuan",
        "status": status,
        "last_probe_at": utc_now(),
        "models": discovered,
        "error": None if discovered else "no_candidate_model_succeeded",
        "errors": errors[:5]
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
