"""Agent loop and progress detection tests with mocked LLM."""

from __future__ import annotations

from pathlib import Path

from local_agent.agent import CodingAgent
from local_agent.config import AgentConfig
from local_agent.models import FinalStatus, ReflectionDecision, ReflectionStatus, RiskLevel


class ScriptedClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0

    def complete(self, prompt, model=None, temperature=0.1, timeout=180, **kwargs):
        self.call_count += 1
        if not self.responses:
            return '{"tool":"final","args":{"answer":"done"}}'
        return self.responses.pop(0)


def test_agent_creates_file_with_scripted_tools(tmp_path: Path, monkeypatch) -> None:
    cfg = AgentConfig.from_args(tmp_path, dry_run=False, no_memory=True, no_git=True, max_steps=4)
    agent = CodingAgent(cfg)
    agent.client = ScriptedClient(
        [
            # planner
            '{"goal":"create file","summary":"simple","tasks":[{"id":"t1","title":"Write","description":"write demo","dependencies":[],"relevant_files":[],"validation_commands":[],"risk_level":"low"}]}',
            # executor
            '{"tool":"write_file","args":{"path":"demo.txt","content":"hello"}}',
            # reflector
            '{"status":"finish","analysis":"ok","next_action":"done","relevant_files":[],"should_replan":false,"risk_level":"low","evidence":[]}',
        ]
    )
    # Bypass planner/reflector network by patching methods to deterministic local behavior.
    from local_agent.planner import Planner as _P
    agent.planner.create_plan = lambda goal, summary, **kw: _P._to_plan(
        agent.planner,
        {
            "goal": goal,
            "summary": "s",
            "tasks": [
                {
                    "id": "t1",
                    "title": "Write",
                    "description": "write demo",
                    "dependencies": [],
                    "relevant_files": [],
                    "validation_commands": [],
                    "risk_level": "low",
                }
            ],
        },
        fallback_goal=goal,
    )
    agent.client = ScriptedClient(
        [
            '{"tool":"write_file","args":{"path":"demo.txt","content":"hello"}}',
        ]
    )
    agent.reflector.reflect = lambda *a, **k: ReflectionDecision(
        status=ReflectionStatus.FINISH,
        analysis="ok",
        next_action="created",
        risk_level=RiskLevel.LOW,
    )
    agent.validator.establish_baseline = lambda: []
    report = agent.run("Create demo.txt")
    assert (tmp_path / "demo.txt").read_text(encoding="utf-8") == "hello"
    assert report.status in {FinalStatus.SUCCESS, FinalStatus.PARTIAL_SUCCESS}


def test_no_progress_detection(tmp_path: Path) -> None:
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True, max_steps=3, max_task_attempts=2)
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
                    "title": "Fail",
                    "description": "fail",
                    "dependencies": [],
                    "relevant_files": [],
                    "validation_commands": [],
                    "risk_level": "low",
                }
            ],
        },
        fallback_goal=goal,
    )
    agent.client = ScriptedClient(
        [
            '{"tool":"run_command","args":{"command":"rm -rf /"}}',
            '{"tool":"run_command","args":{"command":"rm -rf /"}}',
        ]
    )
    decisions = []

    def fake_reflect(task, tool_results, validation_summary, no_progress=False, **kwargs):
        decisions.append(no_progress)
        if no_progress:
            return ReflectionDecision(ReflectionStatus.ABORT, "no progress", "stop")
        return ReflectionDecision(ReflectionStatus.RETRY, "retry", "retry")

    agent.reflector.reflect = fake_reflect
    agent.validator.establish_baseline = lambda: []
    report = agent.run("do bad thing")
    assert True in decisions
    assert report.status in {FinalStatus.FAILED, FinalStatus.PARTIAL_SUCCESS, FinalStatus.BLOCKED, FinalStatus.SUCCESS}
