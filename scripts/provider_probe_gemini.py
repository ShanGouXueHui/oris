#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_key():
    if not SECRETS_PATH.exists():
        return None
    data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    return ((((data.get("models") or {}).get("providers") or {}).get("gemini") or {}).get("apiKey"))

def main():
    key = load_key()
    if not key:
        print(json.dumps({
            "provider_id": "gemini",
            "status": "not_configured",
            "last_probe_at": utc_now(),
            "models": [],
            "error": "missing_api_key"
        }, ensure_ascii=False, indent=2))
        return

    req = urllib.request.Request(
        f"{MODELS_URL}?key={key}",
        headers={"Accept": "application/json", "User-Agent": "ORIS-Provider-Probe/1.0"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models", [])
        discovered = []
        for m in models:
            name = m.get("name")
            if isinstance(name, str) and name:
                discovered.append({"model_id": name, "free_candidate": False})
        print(json.dumps({
            "provider_id": "gemini",
            "status": "healthy",
            "last_probe_at": utc_now(),
            "models": discovered,
            "error": None
        }, ensure_ascii=False, indent=2))
    except urllib.error.HTTPError as e:
        print(json.dumps({
            "provider_id": "gemini",
            "status": "degraded",
            "last_probe_at": utc_now(),
            "models": [],
            "error": f"http_{e.code}"
        }, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "provider_id": "gemini",
            "status": "degraded",
            "last_probe_at": utc_now(),
            "models": [],
            "error": f"{type(e).__name__}: {e}"
        }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
