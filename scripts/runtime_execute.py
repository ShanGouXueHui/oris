#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "orchestration" / "runtime_plan.json"
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def deep_get(data, path):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

def load_secrets():
    if not SECRETS_PATH.exists():
        return {}
    return load_json(SECRETS_PATH)

def get_provider_key(provider_id: str, secrets: dict):
    candidates = {
        "openrouter": [
            ["models", "providers", "openrouter", "apiKey"],
        ],
        "gemini": [
            ["models", "providers", "gemini", "apiKey"],
        ],
        "zhipu": [
            ["models", "providers", "zhipu", "apiKey"],
        ],
        "alibaba_bailian": [
            ["models", "providers", "alibaba_bailian", "apiKey"],
            ["models", "providers", "Alibailian", "apiKey"],
            ["models", "providers", "alibailian", "apiKey"],
            ["models", "providers", "AlibabaBailian", "apiKey"],
        ],
        "tencent_hunyuan": [
            ["models", "providers", "tencent_hunyuan", "apiKey"],
            ["models", "providers", "tencenthunyuan", "apiKey"],
            ["models", "providers", "Tencenthunyuan", "apiKey"],
            ["models", "providers", "tencentHunyuan", "apiKey"],
        ],
    }

    for path in candidates.get(provider_id, []):
        value = deep_get(secrets, path)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def post_json(url: str, headers: dict, body: dict, timeout: int = 60):
    req = urllib.request.Request(
        url,
        headers=headers,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def call_openai_compatible(provider_id: str, model_id: str, prompt: str, api_key: str):
    base_urls = {
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "alibaba_bailian": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "tencent_hunyuan": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
        "zhipu": "https://api.z.ai/api/paas/v4/chat/completions",
    }
    url = base_urls[provider_id]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ORIS-Runtime-Executor/1.0",
    }

    body = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }

    payload = post_json(url, headers, body)
    text = None
    try:
        text = payload["choices"][0]["message"]["content"]
    except Exception:
        text = None

    if not text:
        raise RuntimeError(f"{provider_id} returned no content")
    return {
        "provider_id": provider_id,
        "model_id": model_id,
        "text": text,
        "raw": payload,
    }

def call_gemini(model_id: str, prompt: str, api_key: str):
    clean_model = model_id
    if clean_model.startswith("models/"):
        clean_model = clean_model.split("/", 1)[1]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ORIS-Runtime-Executor/1.0",
    }
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    payload = post_json(url, headers, body)
    text = None
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        text = None

    if not text:
        raise RuntimeError("gemini returned no text")
    return {
        "provider_id": "gemini",
        "model_id": model_id,
        "text": text,
        "raw": payload,
    }

def runtime_feedback(model_id: str, role: str, result: str, error: str = ""):
    cmd = [
        "/usr/bin/python3",
        str(ROOT / "scripts" / "runtime_feedback.py"),
        "--model", model_id,
        "--role", role,
        "--result", result,
    ]
    if error:
        cmd.extend(["--error", error])
    subprocess.run(cmd, check=False, capture_output=True, text=True)

def execute_model(provider_id: str, model_id: str, prompt: str, api_key: str):
    if provider_id in {"openrouter", "alibaba_bailian", "tencent_hunyuan", "zhipu"}:
        return call_openai_compatible(provider_id, model_id, prompt, api_key)
    if provider_id == "gemini":
        return call_gemini(model_id, prompt, api_key)
    raise RuntimeError(f"unsupported provider: {provider_id}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--show-raw", action="store_true")
    args = ap.parse_args()

    plan = load_json(PLAN_PATH)
    role_plan = (plan.get("plans") or {}).get(args.role)
    if not role_plan:
        raise SystemExit(f"role not found in runtime_plan.json: {args.role}")

    failover_chain = role_plan.get("failover_chain", [])
    retry_attempts = int(role_plan.get("retry_attempts", 0))
    backoff = role_plan.get("retry_backoff_seconds", []) or []

    execution_primary = role_plan.get("execution_primary")
    secrets = load_secrets()

    ordered = []
    if execution_primary:
        first = next((x for x in failover_chain if x.get("model_id") == execution_primary), None)
        if first:
            ordered.append(first)
    for item in failover_chain:
        if execution_primary and item.get("model_id") == execution_primary:
            continue
        if item.get("blocked"):
            continue
        ordered.append(item)

    attempts_log = []

    for item in ordered:
        provider_id = item.get("provider_id")
        model_id = item.get("model_id")
        api_key = get_provider_key(provider_id, secrets)

        if not api_key:
            attempts_log.append({
                "provider_id": provider_id,
                "model_id": model_id,
                "status": "skipped",
                "reason": "missing_api_key"
            })
            continue

        max_attempts = 1 + retry_attempts
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                result = execute_model(provider_id, model_id, args.prompt, api_key)
                runtime_feedback(model_id, args.role, "success")
                output = {
                    "ok": True,
                    "role": args.role,
                    "selected_model": role_plan.get("selected_model"),
                    "execution_primary": execution_primary,
                    "used_provider": provider_id,
                    "used_model": model_id,
                    "attempt": attempt,
                    "text": result["text"],
                    "attempts_log": attempts_log,
                }
                if args.show_raw:
                    output["raw"] = result["raw"]
                print(json.dumps(output, ensure_ascii=False, indent=2))
                return
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                attempts_log.append({
                    "provider_id": provider_id,
                    "model_id": model_id,
                    "status": "failure",
                    "attempt": attempt,
                    "error": last_error
                })
                if attempt <= retry_attempts:
                    sleep_s = backoff[attempt - 1] if attempt - 1 < len(backoff) else 1
                    time.sleep(sleep_s)

        runtime_feedback(model_id, args.role, "failure", last_error or "unknown_failure")

    print(json.dumps({
        "ok": False,
        "role": args.role,
        "selected_model": role_plan.get("selected_model"),
        "execution_primary": execution_primary,
        "error": "all_failover_candidates_exhausted",
        "attempts_log": attempts_log,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(2)

if __name__ == "__main__":
    main()
