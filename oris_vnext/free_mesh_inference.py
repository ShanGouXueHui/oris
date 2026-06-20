from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .openai_chat_contract import ChatRequest, legacy_prompt_request


class FreeMeshInference:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.infer_script = repo_root / "scripts" / "oris_infer.py"
        self.latency_log = (
            repo_root / "logs" / "dev_employee" / "free_mesh_latency_events.jsonl"
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _threshold_ms() -> int:
        try:
            return max(1, int(os.getenv("ORIS_FREE_MESH_SLOW_MS", "15000")))
        except Exception:
            return 15000

    @staticmethod
    def warmup_enabled() -> bool:
        return os.getenv("ORIS_FREE_MESH_WARMUP", "1").lower() not in {
            "0",
            "false",
            "no",
        }

    def _append_latency(self, record: dict[str, Any]) -> None:
        self.latency_log.parent.mkdir(parents=True, exist_ok=True)
        with self.latency_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def _private_request_file(request: ChatRequest) -> Path:
        descriptor, name = tempfile.mkstemp(prefix="oris-free-mesh-", suffix=".json")
        path = Path(name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    request.provider_payload(request.model),
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                handle.write("\n")
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            path.unlink(missing_ok=True)
            raise
        return path

    def run(
        self,
        *,
        role: str,
        request: ChatRequest,
        request_id: str,
        source: str = "free_mesh_api",
    ) -> tuple[int, dict[str, Any]]:
        request_path = self._private_request_file(request)
        command = [
            "/usr/bin/python3",
            str(self.infer_script),
            "--role",
            role,
            "--request-file",
            str(request_path),
            "--request-id",
            request_id,
            "--source",
            source,
        ]
        started = time.perf_counter()
        try:
            result = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            request_path.unlink(missing_ok=True)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        stdout = (result.stdout or "").strip()
        if not stdout:
            payload: dict[str, Any] = {
                "ok": False,
                "error": "empty_oris_infer_output",
                "stderr_bytes": len((result.stderr or "").encode("utf-8")),
            }
        else:
            try:
                decoded = json.loads(stdout)
                payload = decoded if isinstance(decoded, dict) else {
                    "ok": False,
                    "error": "invalid_oris_infer_type",
                }
            except json.JSONDecodeError:
                payload = {
                    "ok": False,
                    "error": "invalid_oris_infer_json",
                    "stdout_bytes": len(stdout.encode("utf-8")),
                }
                result = subprocess.CompletedProcess(
                    result.args,
                    2,
                    result.stdout,
                    result.stderr,
                )
        threshold = self._threshold_ms()
        payload.setdefault("latency_ms", elapsed_ms)
        payload.setdefault("slow", elapsed_ms > threshold)
        self._append_latency(
            {
                "ts": self._utc_now(),
                "request_id": request_id,
                "source": source,
                "role": role,
                "ok": bool(payload.get("ok")),
                "elapsed_ms": elapsed_ms,
                "slow": elapsed_ms > threshold,
                "threshold_ms": threshold,
                "used_model": payload.get("used_model"),
                "used_provider": payload.get("used_provider"),
                "finish_reason": payload.get("finish_reason"),
                "tool_call_count": int(payload.get("tool_call_count") or 0),
                **request.metadata(),
            }
        )
        return result.returncode, payload

    def warmup(self) -> None:
        request = legacy_prompt_request(
            "Reply with exactly: ORIS_FREE_MESH_WARMUP_OK"
        )
        try:
            self.run(
                role="primary_general",
                request=request,
                request_id=f"free-mesh-warmup-{uuid.uuid4()}",
                source="free_mesh_warmup",
            )
        except Exception as exc:
            self._append_latency(
                {
                    "ts": self._utc_now(),
                    "source": "free_mesh_warmup",
                    "role": "primary_general",
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "conversation_content_recorded": False,
                }
            )
