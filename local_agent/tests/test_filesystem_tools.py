"""Filesystem tool tests."""

from __future__ import annotations

from pathlib import Path

from local_agent.config import AgentConfig
from local_agent.tools.filesystem import read_file, validate_path, write_file


def test_write_and_validate(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = write_file({"path": "demo.txt", "content": "ok"}, workspace=str(tmp_path), config=cfg)
    assert result.ok
    assert (tmp_path / "demo.txt").read_text(encoding="utf-8") == "ok"
    check = validate_path({"path": "demo.txt"}, workspace=str(tmp_path), config=cfg)
    assert check.ok
    assert check.data["kind"] == "file"


def test_dry_run_write(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, dry_run=True, no_memory=True)
    result = write_file({"path": "demo.txt", "content": "ok"}, workspace=str(tmp_path), config=cfg)
    assert result.ok and result.dry_run
    assert not (tmp_path / "demo.txt").exists()


def test_read_file(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    result = read_file({"path": "a.txt"}, workspace=str(tmp_path), config=cfg)
    assert result.ok
    assert "hello" in result.data["content"]
