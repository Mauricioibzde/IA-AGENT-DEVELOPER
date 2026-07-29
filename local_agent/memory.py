"""Short-term and long-term agent memory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import MemoryEvent
from .security import atomic_write_text, resolve_in_workspace


DEFAULT_LONG_TERM = {
    "project_summary": "",
    "architecture": [],
    "important_files": [],
    "commands": {"test": [], "build": [], "lint": [], "format": []},
    "decisions": [],
    "known_issues": [],
    "coding_conventions": [],
    "last_updated": "",
}


class AgentMemory:
    def __init__(self, workspace: Path, enabled: bool = True) -> None:
        self.workspace = Path(workspace).resolve()
        self.enabled = enabled
        self.short_term: List[MemoryEvent] = []
        self.long_term: Dict[str, Any] = dict(DEFAULT_LONG_TERM)
        self.memory_path = self.workspace / ".agent" / "memory.json"
        if enabled:
            self.load()

    def load(self) -> None:
        if not self.enabled:
            return
        path = self.memory_path
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("memory root must be object")
            merged = dict(DEFAULT_LONG_TERM)
            merged.update(data)
            self.long_term = merged
        except Exception:
            backup = path.with_suffix(".json.corrupt")
            try:
                backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
            self.long_term = dict(DEFAULT_LONG_TERM)
            self.save()

    def save(self) -> None:
        if not self.enabled:
            return
        self.long_term["last_updated"] = datetime.now(timezone.utc).isoformat()
        path = resolve_in_workspace(self.workspace, ".agent/memory.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(self.long_term, ensure_ascii=False, indent=2) + "\n")

    def add_event(self, kind: str, summary: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.short_term.append(MemoryEvent(kind=kind, summary=summary, payload=payload or {}))
        self.short_term = self.short_term[-100:]

    def recent(self, limit: int = 12) -> List[MemoryEvent]:
        return self.short_term[-limit:]

    def relevant_summary(self, limit: int = 8) -> str:
        chunks = []
        if self.long_term.get("project_summary"):
            chunks.append(f"Project summary: {self.long_term['project_summary']}")
        if self.long_term.get("important_files"):
            chunks.append("Important files: " + ", ".join(self.long_term["important_files"][:12]))
        if self.long_term.get("known_issues"):
            chunks.append("Known issues: " + "; ".join(map(str, self.long_term["known_issues"][:5])))
        for event in self.recent(limit):
            detail = ""
            if event.kind in {"tools", "reflection", "validation"} and event.payload:
                detail = f" | {json.dumps(event.payload, ensure_ascii=False)[:200]}"
            chunks.append(f"- [{event.kind}] {event.summary}{detail}")
        if self.long_term.get("decisions"):
            chunks.append("Recent decisions: " + "; ".join(map(str, self.long_term["decisions"][-3:])))
        return "\n".join(chunks)

    def record_decision(self, text: str) -> None:
        decisions = list(self.long_term.get("decisions") or [])
        if text and text not in decisions:
            decisions.append(text[:300])
        self.long_term["decisions"] = decisions[-20:]
        self.save()

    def update_project_summary(self, summary: str) -> None:
        self.long_term["project_summary"] = summary[:2000]
        self.save()

    def remember_files(self, files: List[str]) -> None:
        current = list(self.long_term.get("important_files") or [])
        for item in files:
            if item not in current:
                current.append(item)
        self.long_term["important_files"] = current[:50]
        self.save()
