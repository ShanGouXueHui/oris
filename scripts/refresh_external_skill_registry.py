#!/usr/bin/env python3
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "external_skill_registry.json"
RUNTIME = ROOT / "config" / "external_skill_refresh_runtime.json"

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def append_log(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def parse_github_repo(url: str):
    if not url:
        return None
    m = re.search(r'github\.com/([^/]+)/([^/#?]+)', url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = repo.removesuffix(".git")
    return owner, repo

def github_repo_meta(owner: str, repo: str, timeout: int, ua: str):
    api = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(api, headers={"User-Agent": ua, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    reg = load_json(REGISTRY, {})
    rt = (load_json(RUNTIME, {}) or {}).get("refresh_runtime") or {}
    timeout = int(rt.get("request_timeout_seconds") or 20)
    ua = rt.get("user_agent") or "ORIS-ExternalSkill-Refresh/1.0"
    log_path = ROOT / (rt.get("log_path") or "orchestration/external_skill_refresh_log.jsonl")

    items = reg.get("external_skills") or []
    updated = 0
    results = []

    for item in items:
        repo_url = item.get("repo") or ""
        parsed = parse_github_repo(repo_url)
        if not parsed:
            results.append({"skill_code": item.get("skill_code"), "ok": False, "reason": "not_github_repo"})
            continue

        owner, repo = parsed
        try:
            meta = github_repo_meta(owner, repo, timeout, ua)
            item["refresh_meta"] = {
                "checked_at": now_iso(),
                "full_name": meta.get("full_name"),
                "stargazers_count": meta.get("stargazers_count"),
                "forks_count": meta.get("forks_count"),
                "open_issues_count": meta.get("open_issues_count"),
                "watchers_count": meta.get("watchers_count"),
                "default_branch": meta.get("default_branch"),
                "pushed_at": meta.get("pushed_at"),
                "updated_at": meta.get("updated_at"),
                "html_url": meta.get("html_url")
            }
            updated += 1
            results.append({"skill_code": item.get("skill_code"), "ok": True, "full_name": meta.get("full_name")})
        except Exception as e:
            results.append({"skill_code": item.get("skill_code"), "ok": False, "reason": str(e)[:300]})

    reg["external_skills"] = items
    write_json(REGISTRY, reg)
    append_log(log_path, {
        "ts": now_iso(),
        "updated_count": updated,
        "result_count": len(results),
        "results": results
    })
    print(json.dumps({
        "ok": True,
        "updated_count": updated,
        "result_count": len(results),
        "results": results
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
