"""Per-run filesystem checkpoints for undo/rollback."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class RunCheckpoint:
    """Snapshots file contents before the first mutation of each path in a run."""

    def __init__(self, workspace: Path, run_id: str) -> None:
        self.workspace = Path(workspace).resolve()
        self.run_id = run_id or "anonymous"
        self.dir = self.workspace / ".agent" / "checkpoints"
        self.path = self.dir / f"{self.run_id}.json"
        self.entries: List[Dict[str, Any]] = []
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return
        self.entries = [e for e in entries if isinstance(e, dict) and e.get("path")]
        self._seen = {str(e["path"]) for e in self.entries}

    def _save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": self.run_id,
            "updated": time.time(),
            "entries": self.entries,
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def snapshot_before(self, rel_path: str) -> None:
        rel = str(rel_path or "").replace("\\", "/").lstrip("./")
        if not rel or rel in self._seen or rel.startswith(".agent/"):
            return
        target = (self.workspace / rel).resolve()
        try:
            target.relative_to(self.workspace)
        except ValueError:
            return

        if target.is_file():
            try:
                if target.stat().st_size > 1_500_000:
                    # Skip huge binaries — mark as modified without content.
                    entry = {"path": rel, "kind": "modified", "before": None, "skipped": True}
                else:
                    before = target.read_text(encoding="utf-8")
                    entry = {"path": rel, "kind": "modified", "before": before}
            except (OSError, UnicodeDecodeError):
                entry = {"path": rel, "kind": "modified", "before": None, "skipped": True}
        else:
            entry = {"path": rel, "kind": "created", "before": None}

        self.entries.append(entry)
        self._seen.add(rel)
        self._save()

    def restore(self) -> Dict[str, Any]:
        """Restore workspace to pre-run state for snapshotted paths."""
        restored: List[str] = []
        removed: List[str] = []
        skipped: List[str] = []
        for entry in reversed(self.entries):
            rel = str(entry.get("path") or "")
            if not rel:
                continue
            target = self.workspace / rel
            kind = entry.get("kind")
            if kind == "created":
                if target.is_file():
                    try:
                        target.unlink()
                        removed.append(rel)
                        # Clean empty parents (best-effort, stay inside workspace).
                        parent = target.parent
                        while parent != self.workspace and parent.is_dir() and not any(parent.iterdir()):
                            parent.rmdir()
                            parent = parent.parent
                    except OSError:
                        skipped.append(rel)
                continue
            if entry.get("skipped") or entry.get("before") is None:
                skipped.append(rel)
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(entry["before"]), encoding="utf-8")
                restored.append(rel)
            except OSError:
                skipped.append(rel)
        return {
            "ok": True,
            "run_id": self.run_id,
            "restored": restored,
            "removed": removed,
            "skipped": skipped,
            "total": len(self.entries),
        }

    @classmethod
    def load(cls, workspace: Path, run_id: str) -> Optional["RunCheckpoint"]:
        cp = cls(workspace, run_id)
        if not cp.entries and not cp.path.is_file():
            return None
        return cp
