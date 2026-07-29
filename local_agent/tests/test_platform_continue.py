"""Tests for continued agent/platform improvements."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from local_agent.agent import CodingAgent
from local_agent.config import AgentConfig
from local_agent.models import FinalStatus, ReflectionStatus, Task
from local_agent.planner import Planner
from local_agent.project_index import ProjectIndex
from local_agent.reflector import Reflector
from local_agent.validator import Validator
from local_agent.web_scaffold import (
    looks_like_fastapi_goal,
    looks_like_offline_scaffold_goal,
    looks_like_react_goal,
    validate_plain_web,
    write_fastapi_app,
    write_plain_web_app,
)
from ia_platform.dev_server import DevServerManager
from ia_platform.project_templates import get_template_files


class BoomClient:
    def check_available(self, timeout: int = 5) -> bool:
        return False

    def complete(self, *a, **k):
        raise RuntimeError("ollama offline")


def test_reflector_heuristic_finishes_on_success() -> None:
    reflector = Reflector(client=None, model="x")  # type: ignore[arg-type]
    task = Task(id="t1", title="t", description="d", attempts=1, max_attempts=3)
    decision = reflector._heuristic(task, '[{"tool":"write_file","ok":true}]', "No validations executed.")
    assert decision.status == ReflectionStatus.FINISH


def test_react_and_fastapi_goal_detectors() -> None:
    assert looks_like_react_goal("crie um app React com Vite")
    assert looks_like_fastapi_goal("criar uma API FastAPI com /health")
    assert looks_like_offline_scaffold_goal("criar app react")
    assert looks_like_offline_scaffold_goal("criar api fastapi")


def test_offline_react_scaffold(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    agent = CodingAgent(cfg)
    agent.client = BoomClient()  # type: ignore[assignment]
    report = agent.run("criar um app React com Vite simples")
    assert report.status == FinalStatus.SUCCESS
    assert (tmp_path / "package.json").is_file()
    assert (tmp_path / "src" / "App.jsx").is_file()


def test_offline_fastapi_scaffold(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    agent = CodingAgent(cfg)
    agent.client = BoomClient()  # type: ignore[assignment]
    report = agent.run("criar uma API FastAPI com endpoint /health")
    assert report.status == FinalStatus.SUCCESS
    assert (tmp_path / "main.py").is_file()
    assert "FastAPI" in (tmp_path / "main.py").read_text(encoding="utf-8")


def test_api_template_is_fastapi() -> None:
    files = get_template_files("api", "demo-api")
    assert "main.py" in files
    assert "fastapi" in files["main.py"].lower()
    assert "tests/test_health.py" in files


def test_validate_plain_web(tmp_path: Path) -> None:
    write_plain_web_app(tmp_path, "app html css")
    assert validate_plain_web(tmp_path) == []
    (tmp_path / "app.js").unlink()
    problems = validate_plain_web(tmp_path)
    assert any("app.js" in p for p in problems)


def test_baseline_failures_are_pre_existing(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    index = ProjectIndex(tmp_path)
    index.detected_commands = {"test": ['python3 -c "raise SystemExit(1)"'], "lint": [], "build": []}
    validator = Validator(cfg, index)
    results = validator.establish_baseline()
    assert results
    assert all(not r.success for r in results)
    assert all(r.category == "pre_existing" for r in results)
    assert validator.baseline_failures


def test_plan_normalizes_duplicate_and_cycle_deps() -> None:
    client = MagicMock()
    planner = Planner(client, "m")
    plan = planner._to_plan(
        {
            "goal": "g",
            "summary": "s",
            "tasks": [
                {"id": "a", "title": "A", "description": "d", "dependencies": ["b"]},
                {"id": "a", "title": "A2", "description": "d", "dependencies": ["a"]},
                {"id": "b", "title": "B", "description": "d", "dependencies": ["missing", "a"]},
            ],
        },
        fallback_goal="g",
    )
    ids = [t.id for t in plan.tasks]
    assert len(ids) == len(set(ids))
    by_id = {t.id: t for t in plan.tasks}
    assert "missing" not in by_id["b"].dependencies
    for task in plan.tasks:
        assert task.id not in task.dependencies


def test_detect_fastapi_dev_script(tmp_path: Path) -> None:
    write_fastapi_app(tmp_path, "criar api fastapi")
    mgr = DevServerManager()
    assert mgr.detect_dev_script(tmp_path) == "uvicorn"
    status = mgr.status("api-demo", tmp_path)
    assert status["has_dev_script"] is True
    assert status["runtime"] == "uvicorn"


def test_baseline_detects_changed_diagnostics_as_introduced(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    index = ProjectIndex(tmp_path)
    index.detected_commands = {"test": ['python3 -c "raise SystemExit(1)"'], "lint": [], "build": []}
    validator = Validator(cfg, index)
    baseline = validator.establish_baseline()
    assert baseline and baseline[0].category == "pre_existing"
    # Same exit, different diagnostic text → regression.
    validator.baseline_fingerprints[baseline[0].command] = "different-fp"
    again = validator.run_one(baseline[0].command)
    assert again.success is False
    assert again.category == "introduced"


def test_recommend_setup_prefers_installed_coder() -> None:
    from ia_platform.model_catalog import recommend_setup_model

    hw = {"tier": "low", "effective_memory_gb": 5.0, "has_gpu": False, "gpus": []}
    assert recommend_setup_model(hw, ["deepseek-coder:6.7b"]) == "deepseek-coder:6.7b"
