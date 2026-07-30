"""Checkpoint journal / undo tests."""

from __future__ import annotations

from pathlib import Path

from local_agent.agent import CodingAgent
from local_agent.checkpoint import RunCheckpoint
from local_agent.config import AgentConfig
from local_agent.executor import Executor
from local_agent.logging_config import AgentLogger
from local_agent.models import FinalStatus
from local_agent.tools import build_default_registry


def test_checkpoint_restore_created_and_modified(tmp_path: Path) -> None:
    existing = tmp_path / "keep.txt"
    existing.write_text("old\n", encoding="utf-8")
    cp = RunCheckpoint(tmp_path, "run1")
    cp.snapshot_before("keep.txt")
    cp.snapshot_before("new.txt")
    existing.write_text("new\n", encoding="utf-8")
    (tmp_path / "new.txt").write_text("created\n", encoding="utf-8")
    result = cp.restore()
    assert existing.read_text(encoding="utf-8") == "old\n"
    assert not (tmp_path / "new.txt").exists()
    assert "keep.txt" in result["restored"]
    assert "new.txt" in result["removed"]


def test_executor_snapshots_before_write(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    cfg.run_id = "exec1"
    cp = RunCheckpoint(tmp_path, "exec1")
    executor = Executor(build_default_registry(include_git=False), cfg, AgentLogger(cfg), checkpoint=cp)
    executor.run_calls([{"tool": "write_file", "args": {"path": "a.txt", "content": "hi"}}])
    assert (tmp_path / "a.txt").is_file()
    assert any(e["path"] == "a.txt" and e["kind"] == "created" for e in cp.entries)
    cp.restore()
    assert not (tmp_path / "a.txt").exists()


def test_offline_scaffold_writes_checkpoint(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    cfg.run_id = "scaf1"
    agent = CodingAgent(cfg)

    class Boom:
        def check_available(self, timeout: int = 5) -> bool:
            return False

        def complete(self, *a, **k):
            raise RuntimeError("offline")

    agent.client = Boom()  # type: ignore[assignment]
    report = agent.run("criar uma app pequena em HTML CSS e JS")
    assert report.status == FinalStatus.SUCCESS
    cp = RunCheckpoint.load(tmp_path, "scaf1")
    assert cp is not None
    assert any(e["path"] == "index.html" for e in cp.entries)
    result = cp.restore()
    assert "index.html" in result["removed"]
    assert not (tmp_path / "index.html").exists()
