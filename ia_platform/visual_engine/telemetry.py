"""Lightweight Visual Engine telemetry (Phase 8)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_lock = threading.Lock()
_counters: Dict[str, Any] = {
    "compares": 0,
    "captures": 0,
    "suiteRuns": 0,
    "cleanups": 0,
    "errors": 0,
    "lastDurationMs": None,
    "lastOp": None,
    "lastAt": None,
    "totalDurationMs": 0,
}


def record(op: str, *, duration_ms: Optional[float] = None, ok: bool = True) -> None:
    with _lock:
        if op in {"compare", "compare_images", "compare_multi", "pixel_perfect"}:
            _counters["compares"] += 1
            if op in {"compare_multi", "pixel_perfect"}:
                _counters["suiteRuns"] += 1
        elif op == "capture":
            _counters["captures"] += 1
        elif op == "cleanup":
            _counters["cleanups"] += 1
        if not ok:
            _counters["errors"] += 1
        _counters["lastOp"] = op
        _counters["lastAt"] = time.time()
        if duration_ms is not None:
            _counters["lastDurationMs"] = int(duration_ms)
            _counters["totalDurationMs"] = int(_counters["totalDurationMs"]) + int(duration_ms)


def snapshot() -> Dict[str, Any]:
    with _lock:
        return dict(_counters)


def persist(artifacts_root: Path) -> Path:
    root = Path(artifacts_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "telemetry.json"
    payload = {"updated": time.time(), "counters": snapshot()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
