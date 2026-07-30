"""Persisted comparison history under projects/<id>/.agent/visual/."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HISTORY_NAME = "history.json"
MAX_HISTORY = 80


def _history_path(artifacts_root: Path) -> Path:
    return Path(artifacts_root) / HISTORY_NAME


def load_history(artifacts_root: Path) -> List[Dict[str, Any]]:
    path = _history_path(artifacts_root)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict)]


def save_history(artifacts_root: Path, items: List[Dict[str, Any]]) -> None:
    artifacts_root = Path(artifacts_root)
    artifacts_root.mkdir(parents=True, exist_ok=True)
    path = _history_path(artifacts_root)
    payload = {"updated": time.time(), "items": items[:MAX_HISTORY]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_history(artifacts_root: Path, entry: Dict[str, Any]) -> Dict[str, Any]:
    items = load_history(artifacts_root)
    items.insert(0, entry)
    save_history(artifacts_root, items)
    return entry


def get_history_entry(artifacts_root: Path, comparison_id: str) -> Optional[Dict[str, Any]]:
    cid = str(comparison_id or "")
    for item in load_history(artifacts_root):
        if str(item.get("comparisonId") or item.get("id") or "") == cid:
            return item
    # Fallback: directory with report.json
    report = Path(artifacts_root) / cid / "report.json"
    if report.is_file():
        try:
            return json.loads(report.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def delete_comparison(artifacts_root: Path, comparison_id: str) -> bool:
    cid = str(comparison_id or "").strip()
    if not cid or ".." in cid or "/" in cid or "\\" in cid:
        raise ValueError("invalid comparison id")
    root = Path(artifacts_root).resolve()
    target = (root / cid).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escape") from exc
    removed = False
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
        removed = True
    items = [i for i in load_history(root) if str(i.get("comparisonId") or i.get("id") or "") != cid]
    save_history(root, items)
    return removed
