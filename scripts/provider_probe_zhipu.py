#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
CHAT_URL = "https://api.z.ai/api/paas/v4/chat/completions"
CANDIDATE_MODELS = ["glm-4.7-flash", "glm-4.7"]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_key():
    if not SECRETS_PATH.exists():
        return None
    data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    return ((((data.get("models") or {}).get("providers") or {}).get("zhipu") or {}).get("apiKey"))

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
            "provider_id": "zhipu",
            "status": "not_configured",
            "last_probe_at": utc_now(),
            "models": [],
            "error": "missing_api_key"
        }, ensure_ascii=False, indent=2))
        return

    last_error = None

    for model in CANDIDATE_MODELS:
        try:
            _ = try_model(key, model)
            print(json.dumps({
                "provider_id": "zhipu",
                "status": "healthy",
                "last_probe_at": utc_now(),
                "models": [{"model_id": model, "free_candidate": True}],
                "error": None
            }, ensure_ascii=False, indent=2))
            return
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            last_error = {
                "error": f"http_{e.code}",
                "error_body": body,
                "tried_model": model
            }
        except Exception as e:
            last_error = {
                "error": f"{type(e).__name__}: {e}",
                "error_body": "",
                "tried_model": model
            }

    print(json.dumps({
        "provider_id": "zhipu",
        "status": "degraded",
        "last_probe_at": utc_now(),
        "models": [],
        "error": last_error["error"] if last_error else "unknown",
        "error_body": last_error["error_body"] if last_error else "",
        "tried_model": last_error["tried_model"] if last_error else None
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
