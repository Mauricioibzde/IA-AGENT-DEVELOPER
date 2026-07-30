"""Tests for plain HTML/CSS/JS fallback scaffold."""

from __future__ import annotations

from pathlib import Path

from local_agent.agent import CodingAgent
from local_agent.config import AgentConfig
from local_agent.models import FinalStatus
from local_agent.planner import Planner
from local_agent.prompts import minimal_safe_plan
from local_agent.web_scaffold import (
    looks_like_calculator_goal,
    looks_like_offline_scaffold_goal,
    looks_like_plain_web_goal,
    looks_like_react_goal,
    primary_goal,
    workspace_satisfies_calculator,
    write_plain_web_app,
)


class BoomClient:
    def check_available(self, timeout: int = 5) -> bool:
        return False

    def complete(self, *a, **k):
        raise RuntimeError("ollama offline")


class FlakyLlmClient:
    """Ollama 'up' but every completion OOMs — must still scaffold create goals."""

    def check_available(self, timeout: int = 5) -> bool:
        return True

    def complete(self, *a, **k):
        raise RuntimeError("HTTP Error 500: model 'qwen2.5-coder:32b' insufficient memory")

    def stream_chat(self, *a, **k):
        raise RuntimeError("HTTP Error 500: model 'qwen2.5-coder:32b' insufficient memory")


def test_looks_like_plain_web_goal() -> None:
    assert looks_like_plain_web_goal(
        "vamos criar uma pequena aplicacao com html css e javascript algo muito pequeno"
    )
    assert looks_like_plain_web_goal("eu quero criar uma calculadora")
    assert looks_like_calculator_goal("blz ja que estamos falando de matematica eu quero criar uma calculadora")
    assert looks_like_offline_scaffold_goal("quero criar uma calculadora")
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


def test_write_calculator_app(tmp_path: Path) -> None:
    created, title = write_plain_web_app(tmp_path, "quero criar uma calculadora")
    assert title == "Calculadora"
    assert "index.html" in created
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    js = (tmp_path / "app.js").read_text(encoding="utf-8")
    assert "display" in html
    assert "data-op" in html
    assert "compute" in js or "operator" in js


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


def test_agent_scaffolds_calculator_after_llm_oom(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True, max_steps=4)
    agent = CodingAgent(cfg)
    agent.client = FlakyLlmClient()  # type: ignore[assignment]
    report = agent.run("blz ja que estamos falando de matematica eu quero criar uma calculadora")
    assert report.status == FinalStatus.SUCCESS
    assert (tmp_path / "index.html").is_file()
    assert "Calculadora" in (tmp_path / "index.html").read_text(encoding="utf-8")
    assert report.created_files


def test_primary_goal_strips_chat_context() -> None:
    raw = (
        "quero criar uma calculadora\n\n"
        "--- Contexto recente do Chat ---\n"
        "Usuário: regra de 3\n"
        "Agente: vamos usar React e Vite\n"
        "--- Fim do contexto ---"
    )
    assert primary_goal(raw) == "quero criar uma calculadora"
    assert looks_like_calculator_goal(raw)
    assert not looks_like_react_goal(raw)


def test_existing_calculator_short_circuits_success(tmp_path: Path) -> None:
    write_plain_web_app(tmp_path, "criar calculadora")
    assert workspace_satisfies_calculator(tmp_path)
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True, max_steps=4)
    agent = CodingAgent(cfg)
    agent.client = FlakyLlmClient()  # type: ignore[assignment]
    report = agent.run(
        "blz ja que estamos falando de matematica eu quero criar uma calculadora\n\n"
        "--- Contexto recente do Chat ---\nUsuário: regra de 3\n--- Fim do contexto ---"
    )
    assert report.status == FinalStatus.SUCCESS
    assert "já" in report.summary.lower() or "Calculadora" in report.summary


def test_empty_src_dir_does_not_block_scaffold(tmp_path: Path) -> None:
    """Regression: create_directory(src) alone used to skip the safety-net scaffold."""
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True, max_steps=6, max_task_attempts=2)

    class NoToolsThenBudget:
        def __init__(self) -> None:
            self.n = 0

        def check_available(self, timeout: int = 5) -> bool:
            return True

        def complete(self, *a, **k):
            self.n += 1
            if self.n == 1:
                # Planner JSON with one task
                return (
                    '{"summary":"Build calculator with React","tasks":'
                    '[{"id":"task-1","title":"Create app","description":"scaffold",'
                    '"validation_commands":[]}]}'
                )
            return "not a tool call"

        def stream_chat(self, *a, **k):
            self.n += 1
            return "I will create a React app with Python backend..."

        def stats(self):
            return {"budget_remaining": 10}

    agent = CodingAgent(cfg)
    client = NoToolsThenBudget()
    agent.client = client  # type: ignore[assignment]
    # Pretend a prior failed step already created an empty src/
    (tmp_path / "src").mkdir()
    agent.executor.created_files.append("src")
    report = agent.run("eu quero criar uma calculadora")
    assert report.status == FinalStatus.SUCCESS
    assert (tmp_path / "index.html").is_file()
    assert workspace_satisfies_calculator(tmp_path)


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
