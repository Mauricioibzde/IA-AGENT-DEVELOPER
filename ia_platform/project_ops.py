"""Project management helpers: rename, duplicate, archive."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


ARCHIVE_DIRNAME = ".archive"
IGNORE_COPY = {"node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build"}


def list_projects(projects_root: Path, *, query: str = "", include_archived: bool = False) -> List[Dict[str, Any]]:
    projects_root.mkdir(parents=True, exist_ok=True)
    q = query.strip().lower()
    projects: List[Dict[str, Any]] = []

    def _collect(base: Path, archived: bool) -> None:
        if not base.exists():
            return
        for entry in sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if q and q not in entry.name.lower():
                continue
            files = list(entry.rglob("*"))
            file_count = sum(
                1
                for f in files
                if f.is_file() and not any(part in IGNORE_COPY or part.startswith(".") for part in f.parts)
            )
            projects.append(
                {
                    "id": entry.name if not archived else f".archive/{entry.name}",
                    "name": entry.name,
                    "path": f"projects/{entry.name}" if not archived else f"projects/.archive/{entry.name}",
                    "files": file_count,
                    "updated": entry.stat().st_mtime,
                    "archived": archived,
                }
            )

    _collect(projects_root, False)
    if include_archived:
        _collect(projects_root / ARCHIVE_DIRNAME, True)
    return projects


def rename_project(projects_root: Path, project_id: str, new_name: str, safe_name_fn) -> Dict[str, Any]:
    src = (projects_root / project_id).resolve()
    if not str(src).startswith(str(projects_root.resolve())) or not src.is_dir():
        raise ValueError("project not found")
    dest_name = safe_name_fn(new_name)
    dest = projects_root / dest_name
    if dest.exists():
        raise ValueError("target name already exists")
    src.rename(dest)
    return {"id": dest_name, "name": dest_name, "path": f"projects/{dest_name}"}


def duplicate_project(projects_root: Path, project_id: str, safe_name_fn) -> Dict[str, Any]:
    src = (projects_root / project_id).resolve()
    if not str(src).startswith(str(projects_root.resolve())) or not src.is_dir():
        raise ValueError("project not found")
    base = safe_name_fn(f"{project_id}-copy")
    dest = projects_root / base
    if dest.exists():
        for i in range(2, 100):
            candidate = projects_root / f"{base}-{i}"
            if not candidate.exists():
                dest = candidate
                break
    def _ignore(directory: str, names: List[str]):
        return {n for n in names if n in IGNORE_COPY or n.startswith(".git")}

    shutil.copytree(src, dest, ignore=_ignore)
    return {"id": dest.name, "name": dest.name, "path": f"projects/{dest.name}"}


def archive_project(projects_root: Path, project_id: str) -> Dict[str, Any]:
    src = (projects_root / project_id).resolve()
    if not str(src).startswith(str(projects_root.resolve())) or not src.is_dir():
        raise ValueError("project not found")
    archive_root = projects_root / ARCHIVE_DIRNAME
    archive_root.mkdir(parents=True, exist_ok=True)
    dest = archive_root / project_id
    if dest.exists():
        for i in range(2, 100):
            candidate = archive_root / f"{project_id}-{i}"
            if not candidate.exists():
                dest = candidate
                break
    src.rename(dest)
    return {"id": dest.name, "archived": True, "path": f"projects/.archive/{dest.name}"}
