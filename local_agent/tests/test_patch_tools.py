"""Patch tool tests."""

from __future__ import annotations

from pathlib import Path

from local_agent.config import AgentConfig
from local_agent.tools.patch_tools import apply_patch


def test_apply_unique_hunk(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = apply_patch(
        {"path": "file.txt", "hunks": [{"old": "beta", "new": "BETA"}]},
        workspace=str(tmp_path),
        config=cfg,
    )
    assert result.ok
    assert "BETA" in path.read_text(encoding="utf-8")


def test_reject_ambiguous_hunk(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("x\nx\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = apply_patch(
        {"path": "file.txt", "hunks": [{"old": "x", "new": "y"}]},
        workspace=str(tmp_path),
        config=cfg,
    )
    assert not result.ok
    assert "ambiguous" in (result.error or "").lower()


def test_dry_run_patch(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("one", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, dry_run=True, no_memory=True)
    result = apply_patch(
        {"path": "file.txt", "hunks": [{"old": "one", "new": "two"}]},
        workspace=str(tmp_path),
        config=cfg,
    )
    assert result.ok and result.dry_run
    assert path.read_text(encoding="utf-8") == "one"
