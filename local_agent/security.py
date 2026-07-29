"""Workspace sandboxing and path safety helpers."""

from __future__ import annotations

import os
from pathlib import Path


class WorkspaceSecurityError(ValueError):
    """Raised when a tool tries to escape the workspace sandbox."""


def resolve_in_workspace(
    workspace: str | Path,
    raw_path: str | Path | None,
    default: str = ".",
    *,
    allow_missing: bool = True,
) -> Path:
    """Resolve a path and ensure it stays inside the workspace root.

    Symlinks that resolve outside the workspace are rejected.
    """
    workspace_root = Path(workspace).resolve()
    candidate = Path(default if raw_path in (None, "") else raw_path)

    if candidate.is_absolute():
        # Resolve without requiring existence first.
        resolved = candidate
        if candidate.exists() or candidate.is_symlink():
            resolved = candidate.resolve()
        else:
            resolved = Path(os.path.normpath(str(candidate)))
    else:
        joined = workspace_root / candidate
        if joined.exists() or joined.is_symlink():
            resolved = joined.resolve()
        else:
            resolved = Path(os.path.normpath(str(joined)))

    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise WorkspaceSecurityError(
            f"Path escapes workspace: {raw_path!r} -> {resolved} (workspace={workspace_root})"
        ) from exc

    # Extra symlink parent check: if any parent is a symlink leaving workspace.
    current = resolved
    for parent in [current, *current.parents]:
        if parent == workspace_root:
            break
        if parent.is_symlink():
            target = parent.resolve()
            try:
                target.relative_to(workspace_root)
            except ValueError as exc:
                raise WorkspaceSecurityError(
                    f"Symlink escapes workspace: {parent} -> {target}"
                ) from exc
        if not allow_missing and parent == resolved and not resolved.exists():
            raise FileNotFoundError(f"Path not found: {resolved}")
    return resolved


def is_probably_binary(path: Path, sample_size: int = 2048) -> bool:
    if not path.is_file():
        return False
    try:
        chunk = path.read_bytes()[:sample_size]
    except OSError:
        return True
    if b"\x00" in chunk:
        return True
    # High ratio of non-text bytes.
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
    nontext = chunk.translate(None, text_chars)
    return bool(chunk) and (len(nontext) / len(chunk)) > 0.30


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)
