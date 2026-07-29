"""Track in-flight agent runs, workspace locks, and cancellation requests."""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Dict, Optional, Set


class RunManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled: Set[str] = set()
        self._active: Set[str] = set()
        self._workspace_runs: Dict[str, str] = {}

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
        return run_id

    def create(self) -> str:
        """Create a run id without workspace locking (tests / cancel API)."""
        run_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._active.add(run_id)
        return run_id

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

    def clear(self, run_id: str) -> None:
        with self._lock:
            self._active.discard(run_id)
            self._cancelled.discard(run_id)
            for workspace, active_id in list(self._workspace_runs.items()):
                if active_id == run_id:
                    del self._workspace_runs[workspace]
                    break

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)


run_manager = RunManager()
