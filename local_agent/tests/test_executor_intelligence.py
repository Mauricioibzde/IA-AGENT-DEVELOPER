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


def test_mutation_budget_allows_reedit_same_file(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    cfg.max_modified_files = 1
    executor = Executor(build_default_registry(include_git=False), cfg, AgentLogger(cfg))
    r1, _ = executor.run_calls([{"tool": "write_file", "args": {"path": "a.txt", "content": "1"}}])
    assert r1[0]["result"]["ok"] is True
    r2, _ = executor.run_calls([{"tool": "write_file", "args": {"path": "a.txt", "content": "2"}}])
    assert r2[0]["result"]["ok"] is True
    r3, _ = executor.run_calls([{"tool": "write_file", "args": {"path": "b.txt", "content": "x"}}])
    assert r3[0]["result"]["ok"] is False
    assert "budget" in r3[0]["result"]["error"].lower()


def test_create_multiple_files_respects_budget(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    cfg.max_modified_files = 2
    executor = Executor(build_default_registry(include_git=False), cfg, AgentLogger(cfg))
    results, _ = executor.run_calls(
        [
            {
                "tool": "create_multiple_files",
                "args": {
                    "files": [
                        {"path": "a.txt", "content": "a"},
                        {"path": "b.txt", "content": "b"},
                        {"path": "c.txt", "content": "c"},
                    ]
                },
            }
        ]
    )
    assert results[0]["result"]["ok"] is False
    assert "budget" in results[0]["result"]["error"].lower()
