"""Track in-flight agent runs, workspace locks, cancellation, and event buffers."""

from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Hard cap: free any lock older than this (covers crashed servers / hung workers).
MAX_LOCK_AGE_SECONDS = 45 * 60
# After cancel, free quickly if the agent never cleared (stuck in LLM stream).
CANCELLED_GRACE_SECONDS = 45
# No events for this long → treat as zombie and free (UI lost SSE but lock lingered).
STALE_IDLE_SECONDS = 12 * 60


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

    def _free_workspace_locked(self, workspace_key: str, run_id: str, status: str) -> None:
        self._active.discard(run_id)
        self._workspace_runs.pop(workspace_key, None)
        meta = self._meta.setdefault(run_id, {})
        meta["status"] = status

    def _maybe_free_stale_locked(self, workspace_key: str, run_id: str) -> bool:
        """Free zombie locks. Returns True if the lock was freed (workspace no longer busy)."""
        meta = self._meta.get(run_id) or {}
        now = time.time()
        started = float(meta.get("started_at") or 0)
        last_event = float(meta.get("last_event_at") or started or 0)

        if run_id in self._cancelled and started and now - started > CANCELLED_GRACE_SECONDS:
            self._free_workspace_locked(workspace_key, run_id, "cancelled")
            return True
        if started and now - started > MAX_LOCK_AGE_SECONDS:
            self._free_workspace_locked(workspace_key, run_id, "expired")
            return True
        if last_event and now - last_event > STALE_IDLE_SECONDS:
            self._free_workspace_locked(workspace_key, run_id, "stale")
            return True
        return False

    def acquire(self, workspace: str) -> Optional[str]:
        """Reserve a run for a workspace. Returns run_id or None if busy."""
        workspace_key = self._normalize_workspace(workspace)
        run_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock:
            existing = self._workspace_runs.get(workspace_key)
            if existing:
                if not self._maybe_free_stale_locked(workspace_key, existing):
                    return None
            self._workspace_runs[workspace_key] = run_id
            self._active.add(run_id)
            self._events[run_id] = []
            self._meta[run_id] = {
                "workspace": workspace_key,
                "started_at": now,
                "last_event_at": now,
                "status": "running",
            }
            self._finished_until.pop(run_id, None)
        return run_id

    def create(self) -> str:
        """Create a run id without workspace locking (tests / cancel API)."""
        run_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock:
            self._active.add(run_id)
            self._events[run_id] = []
            self._meta[run_id] = {
                "workspace": None,
                "started_at": now,
                "last_event_at": now,
                "status": "running",
            }
        return run_id

    def append_event(self, run_id: str, event: Dict[str, Any]) -> int:
        """Append an event and return its 1-based sequence number."""
        with self._lock:
            bucket = self._events.setdefault(run_id, [])
            seq = len(bucket) + 1
            payload = dict(event)
            payload["_seq"] = seq
            bucket.append(payload)
            meta = self._meta.setdefault(run_id, {})
            meta["last_event_at"] = time.time()
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
                "last_event_at": meta.get("last_event_at"),
                "goal": meta.get("goal"),
            }

    def active_for_workspace(self, workspace: str) -> Optional[Dict[str, Any]]:
        workspace_key = self._normalize_workspace(workspace)
        with self._lock:
            run_id = self._workspace_runs.get(workspace_key)
            if not run_id:
                return None
            if self._maybe_free_stale_locked(workspace_key, run_id):
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
                "last_event_at": meta.get("last_event_at"),
                "goal": meta.get("goal"),
            }

    def set_goal(self, run_id: str, goal: str) -> None:
        with self._lock:
            meta = self._meta.setdefault(run_id, {})
            meta["goal"] = goal
            meta["last_event_at"] = time.time()

    def cancel(self, run_id: str, *, force: bool = False) -> bool:
        """Mark a run cancelled. With force=True, free the workspace lock immediately."""
        with self._lock:
            known = run_id in self._active or any(rid == run_id for rid in self._workspace_runs.values())
            if not known:
                return False
            self._cancelled.add(run_id)
            meta = self._meta.setdefault(run_id, {})
            meta["status"] = "cancelling" if not force else "cancelled"
            meta["last_event_at"] = time.time()
            if force:
                self._active.discard(run_id)
                meta["status"] = "cancelled"
                for workspace, active_id in list(self._workspace_runs.items()):
                    if active_id == run_id:
                        del self._workspace_runs[workspace]
                        break
            return True

    def cancel_workspace(self, workspace: str, *, force: bool = True) -> Optional[str]:
        """Cancel the active run for a workspace. Returns run_id if any."""
        workspace_key = self._normalize_workspace(workspace)
        with self._lock:
            run_id = self._workspace_runs.get(workspace_key)
            if not run_id:
                return None
        self.cancel(run_id, force=force)
        return run_id

    def is_cancelled(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._cancelled

    def is_workspace_busy(self, workspace: str) -> bool:
        workspace_key = self._normalize_workspace(workspace)
        with self._lock:
            run_id = self._workspace_runs.get(workspace_key)
            if not run_id:
                return False
            if self._maybe_free_stale_locked(workspace_key, run_id):
                return False
            return True

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
