from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime_v2_run_store import InvalidTransitionError, RuntimeV2RunStore, utc_now

TaskExecutor = Callable[[Dict[str, Any], int], Dict[str, Any]]


class RuntimeV2Worker:
    def __init__(self, store: RuntimeV2RunStore, worker_id: str, max_repair_attempts: int = 1) -> None:
        self.store = store
        self.worker_id = worker_id
        self.max_repair_attempts = max_repair_attempts

    def run_once(self, executor: Optional[TaskExecutor] = None) -> Dict[str, Any]:
        item = self.store.claim_next(self.worker_id)
        if item is None:
            return self._iteration("IDLE", None, None, "no_queued_item", 0)

        run = self.store.get_run(item["run_id"])
        if run["state"] in {"COMPLETED", "FAILED_FATAL", "CANCELLED"}:
            self.store.ack_queue_item(item["queue_id"])
            return self._iteration("SKIPPED_TERMINAL", run["run_id"], item["queue_id"], "terminal_run_skipped", 0)

        self._drive_to_running(run["run_id"])
        run = self.store.get_run(run["run_id"])

        task_executor = executor or self._default_success_executor
        attempts = 0
        while True:
            outcome = task_executor(run, attempts)
            outcome_type = outcome.get("type", "success")

            if outcome_type == "success":
                self._complete_successfully(run["run_id"])
                self.store.ack_queue_item(item["queue_id"])
                self._record_worker_event(run["run_id"], "WORKER_ITERATION_COMPLETED", {"queue_id": item["queue_id"], "attempts": attempts})
                status = "REPAIRED" if attempts > 0 else "COMPLETED"
                return self._iteration(status, run["run_id"], item["queue_id"], "success", attempts)

            if outcome_type == "approval_required":
                self.store.transition_run(run["run_id"], "WAITING_APPROVAL", actor=self.worker_id, reason=outcome.get("reason", "approval_required"))
                self._record_worker_event(run["run_id"], "WORKER_WAITING_APPROVAL", {"queue_id": item["queue_id"], "reason": outcome.get("reason", "")})
                return self._iteration("WAITING_APPROVAL", run["run_id"], item["queue_id"], "approval_required", attempts)

            if outcome_type == "fatal":
                self._fail_fatally(run["run_id"], outcome.get("reason", "fatal"))
                self.store.ack_queue_item(item["queue_id"])
                self._record_worker_event(run["run_id"], "WORKER_FATAL_FAILURE", {"queue_id": item["queue_id"], "reason": outcome.get("reason", "")})
                return self._iteration("FAILED_FATAL", run["run_id"], item["queue_id"], "fatal", attempts)

            if outcome_type == "retryable":
                if attempts >= self.max_repair_attempts:
                    self._fail_fatally(run["run_id"], "retry_budget_exhausted")
                    self.store.ack_queue_item(item["queue_id"])
                    return self._iteration("FAILED_FATAL", run["run_id"], item["queue_id"], "retry_budget_exhausted", attempts)
                self.store.transition_run(run["run_id"], "FAILED_RETRYABLE", actor=self.worker_id, reason=outcome.get("reason", "retryable"))
                self.store.transition_run(run["run_id"], "REPAIRING", actor=self.worker_id, reason="auto_repair")
                self.store.transition_run(run["run_id"], "TESTING", actor=self.worker_id, reason="post_repair_test")
                self._record_worker_event(run["run_id"], "WORKER_REPAIR_ATTEMPTED", {"queue_id": item["queue_id"], "attempt": attempts + 1})
                attempts += 1
                run = self.store.get_run(run["run_id"])
                continue

            self._fail_fatally(run["run_id"], f"unknown_outcome:{outcome_type}")
            self.store.ack_queue_item(item["queue_id"])
            return self._iteration("FAILED_FATAL", run["run_id"], item["queue_id"], "unknown_outcome", attempts)

    def _drive_to_running(self, run_id: str) -> None:
        run = self.store.get_run(run_id)
        if run["state"] == "RECEIVED":
            run = self.store.transition_run(run_id, "PLANNED", actor=self.worker_id, reason="worker_planned")
        if run["state"] == "PLANNED":
            run = self.store.transition_run(run_id, "READY", actor=self.worker_id, reason="worker_ready")
        if run["state"] == "READY":
            self.store.transition_run(run_id, "RUNNING", actor=self.worker_id, reason="worker_running")

    def _complete_successfully(self, run_id: str) -> None:
        run = self.store.get_run(run_id)
        if run["state"] == "RUNNING":
            run = self.store.transition_run(run_id, "TESTING", actor=self.worker_id, reason="tests_started")
        if run["state"] == "TESTING":
            run = self.store.transition_run(run_id, "COMMITTING", actor=self.worker_id, reason="evidence_ready")
        if run["state"] == "COMMITTING":
            self.store.transition_run(run_id, "COMPLETED", actor=self.worker_id, reason="worker_completed")

    def _fail_fatally(self, run_id: str, reason: str) -> None:
        run = self.store.get_run(run_id)
        if run["state"] == "RUNNING":
            self.store.transition_run(run_id, "FAILED_RETRYABLE", actor=self.worker_id, reason=reason)
            self.store.transition_run(run_id, "CANCELLED", actor=self.worker_id, reason="fatal_terminal_stop")
            return
        if run["state"] in {"FAILED_RETRYABLE", "FAILED_BLOCKED"}:
            self.store.transition_run(run_id, "CANCELLED", actor=self.worker_id, reason=reason)
            return
        try:
            self.store.transition_run(run_id, "CANCELLED", actor=self.worker_id, reason=reason)
        except InvalidTransitionError:
            pass

    def _record_worker_event(self, run_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        data = self.store._read()
        self.store._append_event(data, event_type, run_id, payload)
        self.store._write(data)

    def _iteration(self, status: str, run_id: Optional[str], queue_id: Optional[str], decision: str, attempts: int) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "status": status,
            "run_id": run_id,
            "queue_id": queue_id,
            "decision": decision,
            "attempts": attempts,
            "created_at": utc_now(),
        }

    @staticmethod
    def _default_success_executor(run: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        return {"type": "success"}
