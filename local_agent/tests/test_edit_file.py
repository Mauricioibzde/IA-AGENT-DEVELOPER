"""Tests for edit_file line-targeted editing."""

from __future__ import annotations

from pathlib import Path

from local_agent.config import AgentConfig
from local_agent.tools.filesystem import edit_file


def test_edit_replace_unique(tmp_path: Path) -> None:
    f = tmp_path / "code.py"
    f.write_text("line1\nline2\nline3\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = edit_file({"path": "code.py", "old": "line2", "new": "LINE2"}, workspace=str(tmp_path), config=cfg)
    assert result.ok
    assert "LINE2" in f.read_text(encoding="utf-8")


def test_edit_insert_after_line(tmp_path: Path) -> None:
    f = tmp_path / "code.py"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = edit_file({"path": "code.py", "line": 2, "new": "INSERTED"}, workspace=str(tmp_path), config=cfg)
    assert result.ok
    lines = f.read_text(encoding="utf-8").splitlines()
    assert lines[2] == "INSERTED"


def test_edit_replace_near_line(tmp_path: Path) -> None:
    f = tmp_path / "code.py"
    content = "\n".join(f"line{i}" for i in range(1, 31))
    f.write_text(content, encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = edit_file(
        {"path": "code.py", "line": 15, "old": "line15", "new": "REPLACED"},
        workspace=str(tmp_path), config=cfg,
    )
    assert result.ok
    assert "REPLACED" in f.read_text(encoding="utf-8")


def test_edit_ambiguous_without_line(tmp_path: Path) -> None:
    f = tmp_path / "code.py"
    f.write_text("x\nx\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = edit_file({"path": "code.py", "old": "x", "new": "y"}, workspace=str(tmp_path), config=cfg)
    assert not result.ok
    assert "ambiguous" in (result.error or "").lower()


def test_edit_dry_run(tmp_path: Path) -> None:
    f = tmp_path / "code.py"
    f.write_text("hello\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, dry_run=True, no_memory=True)
    result = edit_file({"path": "code.py", "old": "hello", "new": "world"}, workspace=str(tmp_path), config=cfg)
    assert result.ok and result.dry_run
    assert f.read_text(encoding="utf-8") == "hello\n"
