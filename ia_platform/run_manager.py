"""Track in-flight agent runs and cancellation requests."""

from __future__ import annotations

import threading
import uuid
from typing import Dict, Set


class RunManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled: Set[str] = set()
        self._active: Set[str] = set()

    def create(self) -> str:
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

    def clear(self, run_id: str) -> None:
        with self._lock:
            self._active.discard(run_id)
            self._cancelled.discard(run_id)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)


run_manager = RunManager()
