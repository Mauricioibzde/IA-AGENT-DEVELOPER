"""Memory persistence tests."""

from __future__ import annotations

import json
from pathlib import Path

from local_agent.memory import AgentMemory


def test_memory_save_load(tmp_path: Path) -> None:
    mem = AgentMemory(tmp_path, enabled=True)
    mem.update_project_summary("demo project")
    mem.remember_files(["a.py"])
    path = tmp_path / ".agent" / "memory.json"
    assert path.exists()
    loaded = AgentMemory(tmp_path, enabled=True)
    assert loaded.long_term["project_summary"] == "demo project"
    assert "a.py" in loaded.long_term["important_files"]


def test_corrupt_memory_recovers(tmp_path: Path) -> None:
    path = tmp_path / ".agent" / "memory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad", encoding="utf-8")
    mem = AgentMemory(tmp_path, enabled=True)
    assert isinstance(mem.long_term, dict)
    assert path.exists()
    json.loads(path.read_text(encoding="utf-8"))
