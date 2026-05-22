#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "orchestration" / "skill_registry.json"
OUT_JSON = ROOT / "logs" / "dev_employee" / "latest_skill_preflight.json"
OUT_MD = ROOT / "logs" / "dev_employee" / "latest_skill_preflight.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def command_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills", required=True, help="Comma-separated skill keys")
    parser.add_argument("--target-project", default="")
    parser.add_argument("--target-path", default="")
    parser.add_argument("--apply", action="store_true", help="Reserved for future controlled installer")
    args = parser.parse_args()

    registry = load_json(REGISTRY)
    policy = registry.get("policy") or {}
    skills = registry.get("skills") or {}
    requested = [x.strip() for x in args.skills.split(",") if x.strip()]

    items = []
    missing_skills = []
    for key in requested:
        spec = skills.get(key)
        if not spec:
            missing_skills.append(key)
            continue
        commands = spec.get("required_commands") or []
        command_status = {cmd: command_available(cmd) for cmd in commands}
        missing_commands = [cmd for cmd, ok in command_status.items() if not ok]
        python_packages = spec.get("python_packages") or []
        safe_auto_install = bool(spec.get("safe_auto_install"))
        requires_approval = (not safe_auto_install) or bool(missing_commands)
        items.append({
            "skill": key,
            "description": spec.get("description"),
            "safe_auto_install": safe_auto_install,
            "install_scope": spec.get("install_scope"),
            "required_commands": commands,
            "command_status": command_status,
            "missing_commands": missing_commands,
            "python_packages": python_packages,
            "requires_human_approval": requires_approval,
            "notes": spec.get("notes"),
        })

    payload = {
        "ok": not missing_skills,
        "generated_at": utc_now(),
        "target_project": args.target_project,
        "target_path": args.target_path,
        "requested_skills": requested,
        "missing_skills": missing_skills,
        "policy": policy,
        "apply_requested": args.apply,
        "applied": False,
        "items": items,
        "decision": "plan_only. Installation is intentionally not applied by this script.",
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# Dev Employee Skill Preflight\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- target_project: `{args.target_project}`\n"
        f"- target_path: `{args.target_path}`\n"
        f"- requested_skills: `{', '.join(requested)}`\n"
        f"- missing_skills: `{', '.join(missing_skills)}`\n"
        f"- applied: `False`\n"
        "- mode: `plan_only`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": payload["ok"], "json_out": str(OUT_JSON), "md_out": str(OUT_MD)}, ensure_ascii=False))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
