"""Security sandbox tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_agent.security import WorkspaceSecurityError, resolve_in_workspace


def test_blocks_parent_escape(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceSecurityError):
        resolve_in_workspace(tmp_path, "../outside.txt")


def test_blocks_absolute_escape(tmp_path: Path, tmp_path_factory) -> None:
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    with pytest.raises(WorkspaceSecurityError):
        resolve_in_workspace(tmp_path, outside)


def test_allows_inside_relative(tmp_path: Path) -> None:
    target = resolve_in_workspace(tmp_path, "src/app.py")
    assert target == (tmp_path / "src" / "app.py").resolve()


def test_symlink_escape(tmp_path: Path, tmp_path_factory) -> None:
    outside = tmp_path_factory.mktemp("out")
    link = tmp_path / "link"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not available")
    with pytest.raises(WorkspaceSecurityError):
        resolve_in_workspace(tmp_path, "link/file.txt")
