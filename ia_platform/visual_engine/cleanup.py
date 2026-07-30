"""Artifact retention cleanup — age + count; never deletes baselines (Phase 8)."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Set

from .history import load_history, save_history

PROTECTED_DIRS = frozenset({"baselines", "corrections"})
DEFAULT_MAX_AGE_SEC = 7 * 24 * 60 * 60
DEFAULT_MAX_COMPARISONS = 80


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        return 0
    return total


def list_comparison_dirs(artifacts_root: Path) -> List[Dict[str, Any]]:
    root = Path(artifacts_root).resolve()
    if not root.is_dir():
        return []
    items: List[Dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if child.name in PROTECTED_DIRS or child.name.startswith("."):
            continue
        # suites/ is a container — clean children separately
        if child.name == "suites":
            for suite in child.iterdir():
                if suite.is_dir():
                    items.append(_stat_entry(suite, kind="suite"))
            continue
        items.append(_stat_entry(child, kind="comparison"))
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


def _stat_entry(path: Path, *, kind: str) -> Dict[str, Any]:
    try:
        st = path.stat()
        mtime = st.st_mtime
    except OSError:
        mtime = 0.0
    return {
        "id": path.name,
        "path": str(path),
        "kind": kind,
        "mtime": mtime,
        "size": _dir_size(path),
    }


def cleanup_artifacts(
    artifacts_root: Path,
    *,
    max_age_sec: float = DEFAULT_MAX_AGE_SEC,
    max_comparisons: int = DEFAULT_MAX_COMPARISONS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Delete old comparison/suite dirs. Never touches baselines/ or corrections/."""
    root = Path(artifacts_root).resolve()
    now = time.time()
    items = list_comparison_dirs(root)
    to_delete: List[Dict[str, Any]] = []
    kept: List[Dict[str, Any]] = []

    for item in items:
        age = now - float(item["mtime"] or 0)
        if max_age_sec > 0 and age > max_age_sec:
            to_delete.append({**item, "reason": "age"})
        else:
            kept.append(item)

    # Count limit on remaining (newest first already)
    if max_comparisons > 0 and len(kept) > max_comparisons:
        overflow = kept[max_comparisons:]
        kept = kept[:max_comparisons]
        for item in overflow:
            to_delete.append({**item, "reason": "count"})

    deleted: List[Dict[str, Any]] = []
    errors: List[str] = []
    freed = 0
    for item in to_delete:
        path = Path(item["path"])
        try:
            path.relative_to(root)
        except ValueError:
            errors.append(f"skip escape: {path}")
            continue
        if path.name in PROTECTED_DIRS:
            continue
        size = int(item.get("size") or 0)
        if dry_run:
            deleted.append({**item, "dry_run": True})
            freed += size
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=False)
            deleted.append(item)
            freed += size
        except OSError as exc:
            errors.append(f"{path.name}: {exc}")

    if not dry_run and deleted:
        _prune_history(root, {d["id"] for d in deleted})

    return {
        "ok": True,
        "dryRun": dry_run,
        "scanned": len(items),
        "kept": len(kept),
        "deleted": len(deleted),
        "freedBytes": freed,
        "deletedIds": [d["id"] for d in deleted],
        "errors": errors,
        "protected": sorted(PROTECTED_DIRS),
        "maxAgeSec": max_age_sec,
        "maxComparisons": max_comparisons,
    }


def cleanup_stats(artifacts_root: Path) -> Dict[str, Any]:
    items = list_comparison_dirs(artifacts_root)
    total = sum(int(i.get("size") or 0) for i in items)
    baselines = Path(artifacts_root).resolve() / "baselines"
    baseline_count = 0
    if baselines.is_dir():
        baseline_count = sum(1 for p in baselines.iterdir() if p.is_dir())
    return {
        "comparisons": len([i for i in items if i["kind"] == "comparison"]),
        "suites": len([i for i in items if i["kind"] == "suite"]),
        "totalBytes": total,
        "baselines": baseline_count,
        "oldestMtime": min((i["mtime"] for i in items), default=None),
        "newestMtime": max((i["mtime"] for i in items), default=None),
    }


def _prune_history(artifacts_root: Path, deleted_ids: Set[str]) -> None:
    if not deleted_ids:
        return
    items = load_history(artifacts_root)
    filtered = [
        i
        for i in items
        if str(i.get("comparisonId") or i.get("id") or "") not in deleted_ids
    ]
    if len(filtered) != len(items):
        save_history(artifacts_root, filtered)
