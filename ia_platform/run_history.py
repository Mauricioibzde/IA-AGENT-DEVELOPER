"""Persist agent run history per project under .agent/runs.json."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

RUNS_FILENAME = "runs.json"
MAX_RUNS = 40
MAX_REPORT_CHARS = 12000


def _runs_file(project_dir: Path) -> Path:
    return project_dir / ".agent" / RUNS_FILENAME


def load_runs(project_dir: Path, limit: int = 20) -> List[Dict[str, Any]]:
    path = _runs_file(project_dir)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    runs = data.get("runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        return []
    return list(reversed(runs[-limit:]))


def record_run(
    project_dir: Path,
    *,
    goal: str,
    status: str,
    report: str,
    created_files: Optional[List[str]] = None,
    modified_files: Optional[List[str]] = None,
    run_id: Optional[str] = None,
    events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    path = _runs_file(project_dir)
    agent_dir = project_dir / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)

    existing: List[Dict[str, Any]] = []
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("runs"), list):
                existing = data["runs"]
        except (json.JSONDecodeError, OSError):
            existing = []

    entry: Dict[str, Any] = {
        "id": run_id or uuid.uuid4().hex[:12],
        "ts": time.time(),
        "goal": goal[:500],
        "status": status,
        "summary": report[:600],
        "report": report[:MAX_REPORT_CHARS],
        "created_files": list(created_files or [])[:30],
        "modified_files": list(modified_files or [])[:30],
        "events": list(events or [])[-40:],
    }
    existing.append(entry)
    payload = {"runs": existing[-MAX_RUNS:], "updated": time.time()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry
