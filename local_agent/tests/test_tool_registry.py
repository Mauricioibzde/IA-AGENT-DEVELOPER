"""Tool registry tests."""

from __future__ import annotations

from local_agent.models import RiskLevel, ToolDefinition, ToolResult
from local_agent.tool_registry import ToolRegistry


def test_registry_validates_required_args() -> None:
    registry = ToolRegistry()

    def handler(args, **context):
        return ToolResult(ok=True, data=args)

    registry.register(
        ToolDefinition(
            name="demo",
            description="demo",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=handler,
        )
    )
    bad = registry.execute("demo", {})
    assert not bad.ok
    good = registry.execute("demo", {"path": "x"})
    assert good.ok
