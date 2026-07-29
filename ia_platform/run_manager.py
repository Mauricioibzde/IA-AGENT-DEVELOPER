"""Track in-flight agent runs, workspace locks, cancellation, and event buffers."""

from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class RunManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled: Set[str] = set()
        self._active: Set[str] = set()
        self._workspace_runs: Dict[str, str] = {}
        self._events: Dict[str, List[Dict[str, Any]]] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._finished_until: Dict[str, float] = {}

    @staticmethod
    def _normalize_workspace(workspace: str) -> str:
        return str(Path(workspace).resolve())

    def acquire(self, workspace: str) -> Optional[str]:
        """Reserve a run for a workspace. Returns run_id or None if busy."""
        workspace_key = self._normalize_workspace(workspace)
        run_id = uuid.uuid4().hex[:12]
        with self._lock:
            if workspace_key in self._workspace_runs:
                return None
            self._workspace_runs[workspace_key] = run_id
            self._active.add(run_id)
            self._events[run_id] = []
            self._meta[run_id] = {
                "workspace": workspace_key,
                "started_at": time.time(),
                "status": "running",
            }
            self._finished_until.pop(run_id, None)
        return run_id

    def create(self) -> str:
        """Create a run id without workspace locking (tests / cancel API)."""
        run_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._active.add(run_id)
            self._events[run_id] = []
            self._meta[run_id] = {"workspace": None, "started_at": time.time(), "status": "running"}
        return run_id

    def append_event(self, run_id: str, event: Dict[str, Any]) -> int:
        """Append an event and return its 1-based sequence number."""
        with self._lock:
            bucket = self._events.setdefault(run_id, [])
            seq = len(bucket) + 1
            payload = dict(event)
            payload["_seq"] = seq
            bucket.append(payload)
            # Cap memory for very long runs.
            if len(bucket) > 800:
                overflow = len(bucket) - 800
                del bucket[:overflow]
                for idx, item in enumerate(bucket, start=1):
                    item["_seq"] = idx
                seq = len(bucket)
            return seq

    def events_after(self, run_id: str, after: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            bucket = self._events.get(run_id) or []
            return [dict(ev) for ev in bucket if int(ev.get("_seq") or 0) > after]

    def status(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if run_id not in self._active and run_id not in self._events and run_id not in self._finished_until:
                return None
            meta = dict(self._meta.get(run_id) or {})
            events = self._events.get(run_id) or []
            return {
                "run_id": run_id,
                "active": run_id in self._active,
                "cancelled": run_id in self._cancelled,
                "workspace": meta.get("workspace"),
                "status": meta.get("status") or ("running" if run_id in self._active else "done"),
                "event_count": len(events),
                "started_at": meta.get("started_at"),
            }

    def active_for_workspace(self, workspace: str) -> Optional[Dict[str, Any]]:
        workspace_key = self._normalize_workspace(workspace)
        with self._lock:
            run_id = self._workspace_runs.get(workspace_key)
            if not run_id:
                return None
            meta = dict(self._meta.get(run_id) or {})
            events = self._events.get(run_id) or []
            return {
                "run_id": run_id,
                "active": True,
                "cancelled": run_id in self._cancelled,
                "workspace": workspace_key,
                "status": meta.get("status") or "running",
                "event_count": len(events),
                "started_at": meta.get("started_at"),
                "goal": meta.get("goal"),
            }

    def set_goal(self, run_id: str, goal: str) -> None:
        with self._lock:
            meta = self._meta.setdefault(run_id, {})
            meta["goal"] = goal

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            if run_id not in self._active:
                return False
            self._cancelled.add(run_id)
            return True

    def is_cancelled(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._cancelled

    def is_workspace_busy(self, workspace: str) -> bool:
        workspace_key = self._normalize_workspace(workspace)
        with self._lock:
            return workspace_key in self._workspace_runs

    def workspace_for(self, run_id: str) -> Optional[str]:
        with self._lock:
            for workspace, active_id in self._workspace_runs.items():
                if active_id == run_id:
                    return workspace
        return None

    def clear(self, run_id: str, *, keep_events_seconds: float = 120.0) -> None:
        with self._lock:
            self._active.discard(run_id)
            self._cancelled.discard(run_id)
            meta = self._meta.get(run_id)
            if meta is not None:
                meta["status"] = "done"
            for workspace, active_id in list(self._workspace_runs.items()):
                if active_id == run_id:
                    del self._workspace_runs[workspace]
                    break
            if keep_events_seconds > 0 and run_id in self._events:
                self._finished_until[run_id] = time.time() + keep_events_seconds
            else:
                self._events.pop(run_id, None)
                self._meta.pop(run_id, None)
            self._prune_finished_locked()

    def _prune_finished_locked(self) -> None:
        now = time.time()
        for run_id, until in list(self._finished_until.items()):
            if until <= now:
                self._finished_until.pop(run_id, None)
                self._events.pop(run_id, None)
                self._meta.pop(run_id, None)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)


run_manager = RunManager()
