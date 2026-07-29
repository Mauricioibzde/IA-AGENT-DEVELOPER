"""Planner parsing/fallback tests."""

from __future__ import annotations

from local_agent.ollama_client import OllamaClient
from local_agent.planner import Planner
from local_agent.config import AgentConfig


class FakeClient(OllamaClient):
    def __init__(self, responses):
        self.responses = list(responses)
        self.config = AgentConfig.from_args(".", no_memory=True)
        self.logger = None
        self.call_count = 0

    def complete(self, prompt, model=None, temperature=0.1, timeout=180):
        self.call_count += 1
        if not self.responses:
            return "{}"
        return self.responses.pop(0)


def test_valid_plan_json(tmp_path) -> None:
    client = FakeClient(
        [
            '{"goal":"g","summary":"s","tasks":[{"id":"t1","title":"A","description":"d","dependencies":[],"relevant_files":[],"validation_commands":[],"risk_level":"low"}]}'
        ]
    )
    plan = Planner(client, "dummy").create_plan("g", "summary")
    assert plan.goal == "g"
    assert len(plan.tasks) == 1
    assert plan.tasks[0].id == "t1"


def test_invalid_plan_falls_back(tmp_path) -> None:
    client = FakeClient(["not-json", "still-bad"])
    plan = Planner(client, "dummy").create_plan("goal text", "summary")
    assert plan.goal == "goal text"
    assert len(plan.tasks) >= 2
