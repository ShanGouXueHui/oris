#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_openclaw_min_dev_toolchain.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_openclaw_min_dev_toolchain.md"

GATEWAY_SERVICE = Path.home() / ".config" / "systemd" / "user" / "openclaw-gateway.service"
REQUIRED_PATH = "/home/admin/.npm-global/bin:/home/admin/.local/bin:/usr/local/bin:/usr/bin:/bin"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: str, timeout: int = 300) -> dict[str, Any]:
    started = time.time()
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        return {
            "cmd": cmd,
            "rc": p.returncode,
            "stdout": (p.stdout or "")[-12000:],
            "stderr": (p.stderr or "")[-8000:],
            "elapsed_ms": round((time.time() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "rc": 124,
            "stdout": str(exc.stdout or "")[-12000:],
            "stderr": str(exc.stderr or "")[-8000:],
            "elapsed_ms": round((time.time() - started) * 1000),
            "timeout": True,
        }


def which(name: str) -> str | None:
    return shutil.which(name)


def patch_gateway_path(apply: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "service": str(GATEWAY_SERVICE),
        "exists": GATEWAY_SERVICE.exists(),
        "changed": False,
        "before": "",
        "after": "",
    }
    if not GATEWAY_SERVICE.exists():
        result["error"] = "service_file_missing"
        return result
    text = GATEWAY_SERVICE.read_text(encoding="utf-8")
    result["before"] = text
    lines = []
    changed = False
    for line in text.splitlines():
        if line.startswith("Environment=PATH="):
            new_line = f"Environment=PATH={REQUIRED_PATH}"
            if line != new_line:
                changed = True
            lines.append(new_line)
        else:
            lines.append(line)
    if "Environment=PATH=" not in text:
        changed = True
        out = []
        for line in lines:
            out.append(line)
            if line.strip() == "[Service]":
                out.append(f"Environment=PATH={REQUIRED_PATH}")
        lines = out
    result["after"] = "\n".join(lines) + "\n"
    result["changed"] = changed
    if apply and changed:
        backup = GATEWAY_SERVICE.with_suffix(f".service.bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
        shutil.copy2(GATEWAY_SERVICE, backup)
        GATEWAY_SERVICE.write_text(result["after"], encoding="utf-8")
        result["backup"] = str(backup)
    return result


def apt_install_gh(apply: bool) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if which("gh"):
        steps.append(run("gh --version", timeout=20))
        return steps
    if not apply:
        steps.append({"cmd": "install gh", "rc": 0, "stdout": "planned_only", "stderr": ""})
        return steps
    steps.append(run("sudo apt update", timeout=600))
    steps.append(run("sudo apt install -y gh", timeout=600))
    steps.append(run("gh --version || true", timeout=20))
    return steps


def install_opencode(apply: bool) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if which("opencode"):
        steps.append(run("opencode --version || opencode -v || true", timeout=20))
        return steps
    candidates = ["opencode-ai", "@opencode-ai/cli", "@sst/opencode"]
    found = None
    for pkg in candidates:
        probe = run(f"npm view {pkg} version", timeout=60)
        steps.append(probe)
        if probe["rc"] == 0 and (probe.get("stdout") or "").strip():
            found = pkg
            break
    if not found:
        steps.append({"cmd": "npm package lookup", "rc": 2, "stdout": "no opencode npm candidate found", "stderr": ""})
        return steps
    if not apply:
        steps.append({"cmd": f"npm install -g {found}", "rc": 0, "stdout": "planned_only", "stderr": ""})
        return steps
    steps.append(run(f"npm install -g {found}", timeout=900))
    steps.append(run("opencode --version || opencode -v || true", timeout=30))
    return steps


def enable_coding_agent(apply: bool) -> dict[str, Any]:
    cfg = Path.home() / ".openclaw" / "openclaw.json"
    result: dict[str, Any] = {"config": str(cfg), "changed": False}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception as exc:
        result["error"] = repr(exc)
        return result
    skills = data.setdefault("skills", {}).setdefault("entries", {})
    before = skills.get("coding-agent")
    after = before if isinstance(before, dict) else {}
    after["enabled"] = True
    skills["coding-agent"] = after
    result["before"] = before
    result["after"] = after
    result["changed"] = before != after
    if apply and result["changed"]:
        backup = cfg.with_suffix(f".json.bak.coding-agent.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
        shutil.copy2(cfg, backup)
        cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["backup"] = str(backup)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "ok": False,
        "generated_at": utc_now(),
        "apply": bool(args.apply),
        "safety": {
            "does_not_modify_env_files": True,
            "does_not_modify_nginx": True,
            "does_not_modify_production_services": True,
            "may_modify_openclaw_user_services": bool(args.apply),
            "may_install_gh_via_apt": bool(args.apply),
            "may_install_opencode_via_npm": bool(args.apply),
        },
        "before": {
            "gh": which("gh"),
            "opencode": which("opencode"),
            "codex": which("codex"),
            "claude": which("claude"),
            "pi": which("pi"),
        },
        "steps": {},
    }

    payload["steps"]["gateway_path"] = patch_gateway_path(args.apply)
    payload["steps"]["gh_install"] = apt_install_gh(args.apply)
    payload["steps"]["opencode_install"] = install_opencode(args.apply)
    payload["steps"]["coding_agent_enable"] = enable_coding_agent(args.apply)

    if args.apply:
        payload["steps"]["daemon_reload"] = run("systemctl --user daemon-reload", timeout=60)
        payload["steps"]["node_install"] = run("openclaw node install", timeout=180)
        payload["steps"]["node_start"] = run("openclaw node start", timeout=180)
        payload["steps"]["gateway_restart"] = run("systemctl --user restart openclaw-gateway.service && sleep 8", timeout=120)

    payload["after"] = {
        "gh": which("gh"),
        "opencode": which("opencode"),
        "codex": which("codex"),
        "claude": which("claude"),
        "pi": which("pi"),
    }
    payload["verify"] = {
        "node_status": run("openclaw node status 2>&1 || true", timeout=30),
        "nodes_status": run("openclaw nodes status 2>&1 || true", timeout=30),
        "skills_check": run("openclaw skills check --agent main 2>&1 | head -n 240 || true", timeout=60),
        "coding_agent_info": run("openclaw skills info coding-agent --agent main 2>&1 || true", timeout=60),
        "github_info": run("openclaw skills info github --agent main 2>&1 || true", timeout=60),
        "exec_policy": run("openclaw exec-policy show 2>&1 || true", timeout=60),
    }

    has_coding_bin = any(payload["after"].get(x) for x in ["opencode", "codex", "claude", "pi"])
    node_text = json.dumps(payload["verify"].get("node_status"), ensure_ascii=False).lower()
    payload["ok"] = bool((not args.apply) or (has_coding_bin and payload["after"].get("gh") and "running" in node_text))

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# OpenClaw Minimal Dev Toolchain\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- apply: `{payload['apply']}`\n"
        f"- gh: `{payload['after'].get('gh')}`\n"
        f"- opencode: `{payload['after'].get('opencode')}`\n"
        f"- codex: `{payload['after'].get('codex')}`\n"
        f"- claude: `{payload['after'].get('claude')}`\n"
        f"- pi: `{payload['after'].get('pi')}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": payload["ok"], "apply": payload["apply"], "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
