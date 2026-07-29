"""Agent streaming event tests."""

from __future__ import annotations

from pathlib import Path

from local_agent.agent import CodingAgent
from local_agent.config import AgentConfig
from local_agent.models import FinalStatus, Plan, Task


def test_agent_emits_events_with_sink(tmp_path: Path) -> None:
    events = []

    def sink(payload):
        events.append(payload)

    cfg = AgentConfig.from_args(tmp_path, dry_run=True, no_memory=True, no_git=True, max_steps=2, plan_only=True)
    agent = CodingAgent(cfg, event_sink=sink)
    agent.planner.create_plan = lambda goal, summary, **kw: Plan(
        goal=goal,
        summary="plan",
        tasks=[Task(id="t1", title="Setup", description="init")],
    )

    report = agent.run("criar app")
    assert report.status == FinalStatus.DRY_RUN_COMPLETED
    kinds = [e["type"] for e in events]
    assert "started" in kinds
    assert "plan" in kinds
