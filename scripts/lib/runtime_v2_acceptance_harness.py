from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from runtime_v2_approval_gate import ApprovalGateStore
from runtime_v2_evidence_publisher import RuntimeV2EvidencePublisher
from runtime_v2_executor import RuntimeV2Executor
from runtime_v2_run_store import RuntimeV2RunStore, utc_now
from runtime_v2_worker import RuntimeV2Worker


class RuntimeV2AcceptanceHarness:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.store = RuntimeV2RunStore(self.root / "runtime_store.json")
        self.executor = RuntimeV2Executor(self.root / "executor_evidence")
        self.publisher = RuntimeV2EvidencePublisher(self.root)
        self.approvals = ApprovalGateStore(self.root / "approval_store.json", self.store)
        self.worker = RuntimeV2Worker(self.store, "acceptance-worker", max_repair_attempts=1)
        (self.root / "summaries").mkdir(parents=True, exist_ok=True)

    def run_success_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance success", "Module G")
        self.store.enqueue(run["run_id"])
        result = self.worker.run_once(self.executor.as_worker_executor({"action_type": "noop", "payload": {}, "risk_level": "LOW"}))
        return self._scenario_result("success", run["run_id"], result["status"] == "COMPLETED")

    def run_repair_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance repair", "Module G")
        self.store.enqueue(run["run_id"])
        def executor(run_record: Dict[str, Any], attempt: int) -> Dict[str, Any]:
            if attempt == 0:
                self.executor.execute({"action_type": "fail_retryable", "payload": {"reason": "synthetic"}, "risk_level": "LOW"})
                return {"type": "retryable", "reason": "synthetic"}
            self.executor.execute({"action_type": "write_evidence", "payload": {"repaired": True}, "risk_level": "LOW"})
            return {"type": "success"}
        result = self.worker.run_once(executor)
        return self._scenario_result("repair", run["run_id"], result["status"] == "REPAIRED")

    def run_approval_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance approval", "Module G")
        self.store.enqueue(run["run_id"])
        wait_result = self.worker.run_once(self.executor.as_worker_executor({"action_type": "require_approval", "payload": {"reason": "manual gate"}, "risk_level": "HIGH"}))
        approval = self.approvals.create_request_from_worker_result(run["run_id"], wait_result, "require_approval")
        self.approvals.decide(approval["approval_id"], "APPROVE", "control-plane")
        self.store.enqueue(run["run_id"])
        done = self.worker.run_once(self.executor.as_worker_executor({"action_type": "noop", "payload": {}, "risk_level": "LOW"}))
        return self._scenario_result("approval", run["run_id"], done["status"] == "COMPLETED")

    def run_blocked_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance blocked", "Module G")
        self.store.enqueue(run["run_id"])
        wait_result = self.worker.run_once(self.executor.as_worker_executor({"action_type": "require_approval", "payload": {"reason": "manual gate"}, "risk_level": "HIGH"}))
        approval = self.approvals.create_request_from_worker_result(run["run_id"], wait_result, "require_approval")
        self.approvals.decide(approval["approval_id"], "REJECT", "control-plane")
        return self._scenario_result("blocked", run["run_id"], self.store.get_run(run["run_id"])["state"] == "FAILED_BLOCKED")

    def run_all(self) -> Dict[str, Any]:
        scenarios = [
            self.run_success_scenario(),
            self.run_repair_scenario(),
            self.run_approval_scenario(),
            self.run_blocked_scenario(),
        ]
        status = "passed" if all(item["status"] == "passed" for item in scenarios) else "failed"
        summary = {"module": "Runtime v2 Module G", "status": status, "scenarios": scenarios, "created_at": utc_now()}
        (self.root / "summaries" / "acceptance_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return summary

    def _scenario_result(self, scenario_type: str, run_id: str, ok: bool) -> Dict[str, Any]:
        final_state = self.store.get_run(run_id)["state"]
        summary_path = self.root / "summaries" / f"{scenario_type}_{run_id}.json"
        payload = {"scenario_type": scenario_type, "run_id": run_id, "final_state": final_state, "ok": ok}
        summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        artifact_paths = [str(path.relative_to(self.root)) for path in (self.root / "executor_evidence").glob("*.json")]
        artifact_paths.append(str(summary_path.relative_to(self.root)))
        index = self.publisher.build_index(f"Module G {scenario_type}", "passed" if ok else "failed", artifact_paths)
        return {
            "scenario_id": f"{scenario_type}:{run_id}",
            "scenario_type": scenario_type,
            "status": "passed" if ok else "failed",
            "run_id": run_id,
            "final_state": final_state,
            "evidence_index_id": index["index_id"],
        }
