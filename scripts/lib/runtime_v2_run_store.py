from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RunStoreError(Exception):
    pass


class InvalidTransitionError(RunStoreError):
    pass


class NotFoundError(RunStoreError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeV2RunStore:
    def __init__(self, path: Path | str, state_machine_path: Path | str = "schemas/runtime_v2/state_machine.schema.json") -> None:
        self.path = Path(path)
        self.state_machine_path = Path(state_machine_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._states, self._terminal_states, self._transitions = self._load_state_machine()
        if not self.path.exists():
            self._write({"runs": {}, "queue": {}, "events": []})

    def _load_state_machine(self) -> Tuple[set[str], set[str], set[tuple[str, str]]]:
        data = json.loads(self.state_machine_path.read_text(encoding="utf-8"))
        states = set(data["states"])
        terminal_states = set(data["terminal_states"])
        transitions = {tuple(item) for item in data["transitions"]}
        return states, terminal_states, transitions

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def _append_event(self, data: Dict[str, Any], event_type: str, run_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        data["events"].append({
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "run_id": run_id,
            "payload": payload or {},
            "created_at": utc_now(),
        })

    def create_run(self, objective: str, module: str, acceptance_criteria: Optional[List[str]] = None, context_pack_ref: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._read()
        if idempotency_key:
            for run in data["runs"].values():
                if run.get("idempotency_key") == idempotency_key:
                    return run
        run_id = str(uuid.uuid4())
        now = utc_now()
        run = {
            "run_id": run_id,
            "objective": objective,
            "module": module,
            "state": "RECEIVED",
            "idempotency_key": idempotency_key,
            "acceptance_criteria": acceptance_criteria or [],
            "context_pack_ref": context_pack_ref,
            "created_at": now,
            "updated_at": now,
        }
        data["runs"][run_id] = run
        self._append_event(data, "RUN_CREATED", run_id, {"module": module})
        self._write(data)
        return run

    def get_run(self, run_id: str) -> Dict[str, Any]:
        data = self._read()
        if run_id not in data["runs"]:
            raise NotFoundError(f"run not found: {run_id}")
        return data["runs"][run_id]

    def transition_run(self, run_id: str, target_state: str, actor: str = "runtime", reason: str = "") -> Dict[str, Any]:
        data = self._read()
        if run_id not in data["runs"]:
            raise NotFoundError(f"run not found: {run_id}")
        run = data["runs"][run_id]
        source_state = run["state"]
        if source_state in self._terminal_states:
            raise InvalidTransitionError(f"terminal run cannot transition: {source_state} -> {target_state}")
        if target_state not in self._states:
            raise InvalidTransitionError(f"unknown target state: {target_state}")
        if (source_state, target_state) not in self._transitions:
            raise InvalidTransitionError(f"invalid transition: {source_state} -> {target_state}")
        run["state"] = target_state
        run["updated_at"] = utc_now()
        self._append_event(data, "RUN_STATE_TRANSITIONED", run_id, {"from": source_state, "to": target_state, "actor": actor, "reason": reason})
        self._write(data)
        return run

    def enqueue(self, run_id: str, priority: int = 100, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._read()
        if run_id not in data["runs"]:
            raise NotFoundError(f"run not found: {run_id}")
        if idempotency_key:
            for item in data["queue"].values():
                if item.get("idempotency_key") == idempotency_key:
                    return item
        queue_id = str(uuid.uuid4())
        now = utc_now()
        item = {
            "queue_id": queue_id,
            "run_id": run_id,
            "status": "QUEUED",
            "priority": int(priority),
            "worker_id": None,
            "idempotency_key": idempotency_key,
            "created_at": now,
            "updated_at": now,
        }
        data["queue"][queue_id] = item
        self._append_event(data, "QUEUE_ITEM_ENQUEUED", run_id, {"queue_id": queue_id, "priority": priority})
        self._write(data)
        return item

    def claim_next(self, worker_id: str) -> Optional[Dict[str, Any]]:
        data = self._read()
        queued = [item for item in data["queue"].values() if item["status"] == "QUEUED"]
        if not queued:
            return None
        queued.sort(key=lambda item: (item["priority"], item["created_at"]))
        item = queued[0]
        item["status"] = "CLAIMED"
        item["worker_id"] = worker_id
        item["updated_at"] = utc_now()
        self._append_event(data, "QUEUE_ITEM_CLAIMED", item["run_id"], {"queue_id": item["queue_id"], "worker_id": worker_id})
        self._write(data)
        return item

    def ack_queue_item(self, queue_id: str) -> Dict[str, Any]:
        data = self._read()
        if queue_id not in data["queue"]:
            raise NotFoundError(f"queue item not found: {queue_id}")
        item = data["queue"][queue_id]
        item["status"] = "ACKED"
        item["updated_at"] = utc_now()
        self._append_event(data, "QUEUE_ITEM_ACKED", item["run_id"], {"queue_id": queue_id})
        self._write(data)
        return item

    def list_events(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._read()
        events = data["events"]
        if run_id is not None:
            return [event for event in events if event.get("run_id") == run_id]
        return events
