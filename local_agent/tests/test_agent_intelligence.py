"""Tests for context feedback and planner enrichment."""

from __future__ import annotations

import json
from pathlib import Path

from local_agent.context_manager import ContextManager
from local_agent.models import Task
from local_agent.planner import Planner
from local_agent.project_index import ProjectIndex
from local_agent.config import AgentConfig


class FakeClient:
    def complete(self, *args, **kwargs):
        return json.dumps(
            {
                "goal": "build api",
                "summary": "s",
                "tasks": [
                    {
                        "id": "t1",
                        "title": "Implement",
                        "description": "edit main.py and add endpoint",
                        "dependencies": [],
                        "relevant_files": [],
                        "validation_commands": [],
                        "risk_level": "low",
                    }
                ],
            }
        )


def test_planner_enriches_relevant_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    index = ProjectIndex(tmp_path)
    index.build()
    plan = Planner(FakeClient(), "m").create_plan("update main.py", index.summary(), index=index)
    assert plan.tasks[0].relevant_files
    assert any("main.py" in p for p in plan.tasks[0].relevant_files)


def test_planner_uses_node_validation(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "vitest run", "build": "vite build"}}),
        encoding="utf-8",
    )
    index = ProjectIndex(tmp_path)
    index.build()
    plan = Planner(FakeClient(), "m").create_plan("build app", index.summary(), index=index)
    cmds = plan.tasks[0].validation_commands
    assert cmds
    assert any("vitest" in c or "npm" in c or "test" in c for c in cmds)


def test_planner_skips_compileall_for_react_only(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite", "build": "vite build"}}),
        encoding="utf-8",
    )
    (src / "App.jsx").write_text("export default function App(){return null}\n", encoding="utf-8")
    index = ProjectIndex(tmp_path)
    index.build()
    plan = Planner(FakeClient(), "m").create_plan("build react ui", index.summary(), index=index)
    cmds = plan.tasks[0].validation_commands
    joined = " ".join(cmds)
    assert "compileall" not in joined
    assert "npm" in joined or "vite" in joined or not cmds


def test_project_index_search_relevant(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "AuthService.py").write_text("class AuthService:\n    pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# docs\n", encoding="utf-8")
    index = ProjectIndex(tmp_path)
    index.build()
    matches = index.search_relevant("update auth service login", limit=5)
    assert any("AuthService.py" in f.path for f in matches)


def test_context_invalidate_refreshes_cache(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("v1\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True)
    ctx = ContextManager(cfg)
    first = ctx.read_file_for_context(Path("app.py"))
    assert "v1" in (first or "")

    target.write_text("v2\n", encoding="utf-8")
    second = ctx.read_file_for_context(Path("app.py"))
    assert "v1" in (second or "")

    ctx.invalidate("app.py")
    third = ctx.read_file_for_context(Path("app.py"))
    assert "v2" in (third or "")
