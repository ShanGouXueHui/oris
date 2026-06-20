from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


class InferRefresh:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.active_path = repo_root / "orchestration" / "active_routing.json"
        self.plan_path = repo_root / "orchestration" / "runtime_plan.json"
        self.best_effort_scripts = (
            repo_root / "scripts" / "quota_probe.py",
            repo_root / "scripts" / "provider_scoreboard.py",
        )
        self.required_scripts = (
            repo_root / "scripts" / "model_selector.py",
            repo_root / "scripts" / "runtime_plan.py",
        )

    @staticmethod
    def _load(path: Path) -> dict | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    @staticmethod
    def _timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def _ttl_seconds() -> int:
        try:
            return max(0, int(os.getenv("ORIS_INFER_REFRESH_TTL_SECONDS", "600")))
        except Exception:
            return 600

    @staticmethod
    def _forced() -> bool:
        return os.getenv("ORIS_INFER_FORCE_REFRESH", "").lower() in {
            "1",
            "true",
            "yes",
        }

    def _fresh(self, path: Path, ttl: int) -> bool:
        value = self._load(path) or {}
        generated = self._timestamp(
            value.get("generated_at") or value.get("updated_at")
        )
        if generated is None:
            return False
        age = (
            datetime.now(timezone.utc) - generated.astimezone(timezone.utc)
        ).total_seconds()
        return 0 <= age <= ttl

    def _has_role(self, path: Path, container: str, role: str) -> bool:
        value = self._load(path) or {}
        entries = value.get(container)
        return isinstance(entries, dict) and role in entries

    @staticmethod
    def _run(path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/usr/bin/python3", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def preflight(self, required_role: str) -> list[dict]:
        ttl = self._ttl_seconds()
        artifacts_ready = (
            self._fresh(self.active_path, ttl)
            and self._fresh(self.plan_path, ttl)
            and self._has_role(self.active_path, "decisions", required_role)
            and self._has_role(self.plan_path, "plans", required_role)
        )
        if not self._forced() and artifacts_ready:
            return [
                {
                    "stage": "preflight",
                    "script": "refresh_skipped",
                    "reason": "runtime_artifacts_fresh_and_role_present",
                    "ttl_seconds": ttl,
                }
            ]
        warnings: list[dict] = []
        for script in self.best_effort_scripts:
            result = self._run(script)
            if result.returncode != 0:
                warnings.append(
                    {
                        "stage": "preflight",
                        "script": script.name,
                        "returncode": result.returncode,
                    }
                )
        for script in self.required_scripts:
            result = self._run(script)
            if result.returncode != 0:
                raise RuntimeError(f"{script.name} refresh failed")
        if not self._has_role(self.plan_path, "plans", required_role):
            raise RuntimeError("required runtime role missing after refresh")
        return warnings

    def postflight(self) -> list[dict]:
        if os.getenv("ORIS_INFER_POST_REFRESH", "").lower() not in {
            "1",
            "true",
            "yes",
        }:
            return [
                {
                    "stage": "postflight",
                    "script": "refresh_skipped",
                    "reason": "post_refresh_disabled_by_default",
                }
            ]
        warnings: list[dict] = []
        for script in (*self.best_effort_scripts, *self.required_scripts):
            result = self._run(script)
            if result.returncode != 0:
                warnings.append(
                    {
                        "stage": "postflight",
                        "script": script.name,
                        "returncode": result.returncode,
                    }
                )
        return warnings
