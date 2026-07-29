"""Tests for plain HTML/CSS/JS fallback scaffold."""

from __future__ import annotations

from pathlib import Path

from local_agent.agent import CodingAgent
from local_agent.config import AgentConfig
from local_agent.models import FinalStatus
from local_agent.planner import Planner
from local_agent.prompts import minimal_safe_plan
from local_agent.web_scaffold import looks_like_plain_web_goal, write_plain_web_app


class BoomClient:
    def check_available(self, timeout: int = 5) -> bool:
        return False

    def complete(self, *a, **k):
        raise RuntimeError("ollama offline")


def test_looks_like_plain_web_goal() -> None:
    assert looks_like_plain_web_goal(
        "vamos criar uma pequena aplicacao com html css e javascript algo muito pequeno"
    )
    assert not looks_like_plain_web_goal("crie um app React com Vite")


def test_minimal_plan_plain_web_skips_npm() -> None:
    plan = minimal_safe_plan("criar app html css javascript pequena")
    assert "html" in plan["summary"].lower() or "estática" in plan["summary"].lower()
    for task in plan["tasks"]:
        assert not any(str(c).startswith("npm") for c in task.get("validation_commands") or [])


def test_write_plain_web_app(tmp_path: Path) -> None:
    created, title = write_plain_web_app(tmp_path, "contador html")
    assert "index.html" in created
    assert "style.css" in created
    assert "app.js" in created
    assert (tmp_path / "index.html").is_file()
    assert "contador" in (tmp_path / "app.js").read_text(encoding="utf-8").lower() or "count" in (
        tmp_path / "app.js"
    ).read_text(encoding="utf-8").lower()
    assert title


def test_agent_scaffolds_when_ollama_offline(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True, max_steps=4)
    agent = CodingAgent(cfg)
    agent.client = BoomClient()  # type: ignore[assignment]
    report = agent.run("criar uma pequena aplicacao com html css e javascript")
    assert report.status == FinalStatus.SUCCESS
    assert (tmp_path / "index.html").is_file()
    assert (tmp_path / "style.css").is_file()
    assert (tmp_path / "app.js").is_file()
    assert report.created_files


def test_planner_enrichment_clears_npm_for_plain_web(tmp_path: Path) -> None:
    class Client:
        def complete(self, *a, **k):
            return "not-json"

    plan = Planner(Client(), "m").create_plan(  # type: ignore[arg-type]
        "criar site html css javascript simples",
        "empty",
    )
    for task in plan.tasks:
        assert not any(c.startswith("npm") for c in task.validation_commands)
