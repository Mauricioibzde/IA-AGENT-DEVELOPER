"""Tests for agent intelligence improvements (feedback, paths, JSON, continue)."""

from __future__ import annotations

import json
from pathlib import Path

from local_agent.agent import CodingAgent
from local_agent.config import AgentConfig
from local_agent.executor import Executor
from local_agent.json_utils import loads_json_lenient
from local_agent.logging_config import AgentLogger
from local_agent.models import FinalStatus, ReflectionDecision, ReflectionStatus, RiskLevel, Task, TaskStatus
from local_agent.reflector import Reflector
from local_agent.tool_registry import parse_tool_calls
from local_agent.tools import build_default_registry
from local_agent.validator import Validator
from local_agent.project_index import ProjectIndex


def test_parse_trailing_comma_and_prose() -> None:
    raw = 'Sure!\n```json\n{"tool":"read_file","args":{"path":"a.txt",},}\n```'
    calls = parse_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0]["tool"] == "read_file"
    assert calls[0]["args"]["path"] == "a.txt"


def test_loads_json_lenient_balanced() -> None:
    raw = 'Here is the plan: {"status":"continue","analysis":"ok",} trailing junk'
    data = loads_json_lenient(raw)
    assert isinstance(data, dict)
    assert data["status"] == "continue"


def test_format_tool_results_keeps_content(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    agent = CodingAgent(cfg)
    payload = [
        {
            "tool": "read_file",
            "result": {
                "ok": True,
                "path": str(tmp_path / "a.txt"),
                "content": "1: hello world\n2: more",
                "total_lines": 2,
            },
        }
    ]
    text = agent._format_tool_results(payload)
    assert "hello world" in text
    assert "total_lines" in text


def test_signature_differs_for_different_content(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    agent = CodingAgent(cfg)
    a = agent._signature("t1", [{"tool": "write_file", "args": {"path": "a.txt", "content": "one"}}])
    b = agent._signature("t1", [{"tool": "write_file", "args": {"path": "a.txt", "content": "two"}}])
    c = agent._signature("t1", [{"tool": "write_file", "args": {"path": "a.txt", "content": "one"}}])
    assert a != b
    assert a == c


def test_continue_does_not_complete_task(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True, max_steps=3, max_task_attempts=3)
    agent = CodingAgent(cfg)
    from local_agent.planner import Planner as _P

    agent.planner.create_plan = lambda goal, summary, **kw: _P._to_plan(
        agent.planner,
        {
            "goal": goal,
            "summary": "s",
            "tasks": [
                {
                    "id": "t1",
                    "title": "Build",
                    "description": "build app",
                    "dependencies": [],
                    "relevant_files": [],
                    "validation_commands": [],
                    "risk_level": "low",
                }
            ],
        },
        fallback_goal=goal,
    )

    class Client:
        def __init__(self):
            self.n = 0

        def complete(self, *a, **k):
            self.n += 1
            return json.dumps({"tool": "write_file", "args": {"path": f"f{self.n}.txt", "content": "x"}})

    agent.client = Client()
    continue_count = {"n": 0}

    def fake_reflect(*a, **k):
        continue_count["n"] += 1
        return ReflectionDecision(
            status=ReflectionStatus.CONTINUE,
            analysis="more work needed",
            next_action="keep going",
            risk_level=RiskLevel.LOW,
        )

    agent.reflector.reflect = fake_reflect
    agent.validator.establish_baseline = lambda: []
    agent.validator.discover_commands = lambda preferred=None: []
    report = agent.run("build something")
    assert continue_count["n"] >= 1
    # Task should not have been completed solely via CONTINUE
    assert "Build" not in agent.completed_tasks or report.status != FinalStatus.SUCCESS


def test_executor_relative_path_after_write(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    registry = build_default_registry(include_git=False)
    executor = Executor(registry, cfg, AgentLogger(cfg))
    results, _ = executor.run_calls(
        [{"tool": "write_file", "args": {"path": "src/App.jsx", "content": "export default function App(){return null}\n"}}]
    )
    assert results[0]["result"]["ok"] is True
    assert "src/App.jsx" in executor.created_files
    # Edit without explicit read should succeed because write marked it known.
    results2, _ = executor.run_calls(
        [{"tool": "edit_file", "args": {"path": "src/App.jsx", "old": "null", "new": "<div/>"}}]
    )
    assert results2[0]["result"]["ok"] is True, results2


def test_validator_summarize_includes_stdout_diagnostics(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    index = ProjectIndex(tmp_path)
    index.build()
    validator = Validator(cfg, index)
    from local_agent.models import ValidationResult

    summary = validator.summarize(
        [
            ValidationResult(
                command="npm run build",
                success=False,
                exit_code=1,
                stdout="src/App.jsx:12: error TS2304: Cannot find name 'Foo'\n",
                stderr="",
                duration_seconds=0.1,
                category="introduced",
            )
        ]
    )
    assert "App.jsx" in summary
    assert "FAIL" in summary


def test_reflector_soft_no_progress_retries() -> None:
    reflector = Reflector(client=None, model="x")  # type: ignore[arg-type]
    task = Task(id="t1", title="t", description="d", attempts=1, max_attempts=3)
    decision = reflector.reflect(task, "[]", "No validations executed.", no_progress=True, no_progress_count=2)
    assert decision.status == ReflectionStatus.RETRY
    decision2 = reflector.reflect(task, "[]", "No validations executed.", no_progress=True, no_progress_count=3)
    assert decision2.status == ReflectionStatus.REPLAN


def test_ensure_node_dependencies_skips_when_installed(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    index = ProjectIndex(tmp_path)
    index.build()
    validator = Validator(cfg, index)
    assert validator.ensure_node_dependencies() is None
