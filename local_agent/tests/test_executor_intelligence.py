"""Tests for executor intelligence guardrails."""

from __future__ import annotations

from pathlib import Path

from local_agent.config import AgentConfig
from local_agent.executor import Executor
from local_agent.logging_config import AgentLogger
from local_agent.tools import build_default_registry


def test_read_before_edit_blocks_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "existing.py"
    target.write_text("x = 1\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    executor = Executor(build_default_registry(include_git=False), cfg, AgentLogger(cfg))

    results, finished = executor.run_calls(
        [{"tool": "edit_file", "args": {"path": "existing.py", "line": 1, "old": "x = 1", "new": "x = 2"}}]
    )
    assert finished is False
    assert results[0]["result"]["ok"] is False
    assert "read_file" in results[0]["result"]["error"]


def test_read_before_edit_allows_new_file(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    executor = Executor(build_default_registry(include_git=False), cfg, AgentLogger(cfg))

    results, finished = executor.run_calls(
        [{"tool": "write_file", "args": {"path": "new.txt", "content": "hello"}}]
    )
    assert finished is False
    assert results[0]["result"]["ok"] is True
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "hello"


def test_mark_read_allows_edit(tmp_path: Path) -> None:
    target = tmp_path / "existing.py"
    target.write_text("x = 1\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    executor = Executor(build_default_registry(include_git=False), cfg, AgentLogger(cfg))
    executor.mark_read("existing.py")

    results, _ = executor.run_calls(
        [{"tool": "write_file", "args": {"path": "existing.py", "content": "x = 2\n"}}]
    )
    assert results[0]["result"]["ok"] is True
