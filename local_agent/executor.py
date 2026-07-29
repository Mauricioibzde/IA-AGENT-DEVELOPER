"""Tool execution facade on top of the registry."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import AgentConfig
from .logging_config import AgentLogger
from .models import RiskLevel, ToolResult
from .tool_registry import ToolRegistry, infer_tool_call_from_text, parse_tool_calls


class Executor:
    def __init__(self, registry: ToolRegistry, config: AgentConfig, logger: AgentLogger) -> None:
        self.registry = registry
        self.config = config
        self.logger = logger
        self.modified_files: List[str] = []
        self.created_files: List[str] = []
        self.commands: List[str] = []

    def parse_calls(self, model_text: str) -> List[Dict[str, Any]]:
        calls = parse_tool_calls(model_text)
        if calls:
            return calls
        inferred = infer_tool_call_from_text(model_text)
        return [inferred] if inferred else []

    def run_calls(self, calls: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
        """Execute tool calls. Returns (results, finished_with_final)."""
        results: List[Dict[str, Any]] = []
        for call in calls:
            name = call.get("tool")
            args = call.get("args") or {}
            if not name:
                continue
            if name == "final":
                answer = args.get("answer", "") if isinstance(args, dict) else ""
                results.append({"tool": "final", "result": {"ok": True, "answer": answer}})
                return results, True

            tool = self.registry.get(name)
            if tool and tool.requires_confirmation and tool.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
                if not self.config.auto_approve_low_risk:
                    result = ToolResult(
                        ok=False,
                        error=f"Tool {name} requires confirmation (risk={tool.risk_level.value})",
                    )
                    results.append({"tool": name, "result": result.to_dict()})
                    continue

            started = __import__("time").time()
            result = self.registry.execute(
                name,
                args if isinstance(args, dict) else {},
                workspace=str(self.config.workspace),
                config=self.config,
            )
            duration_ms = int((__import__("time").time() - started) * 1000)
            self.logger.info(
                "tool_execution",
                message=f"{name} ok={result.ok}",
                tool=name,
                success=result.ok,
                duration_ms=duration_ms,
            )
            self._track(name, result)
            results.append({"tool": name, "result": result.to_dict()})
        return results, False

    def _track(self, name: str, result: ToolResult) -> None:
        data = result.data
        if name == "run_command" and data.get("command"):
            self.commands.append(str(data["command"]))
        path = data.get("path")
        files = data.get("files")
        if name in {"write_file", "create_file", "create_multiple_files", "scaffold_project"} and result.ok and not result.dry_run:
            if path:
                self.created_files.append(str(path))
            if isinstance(files, list):
                self.created_files.extend(map(str, files))
        if name in {"apply_patch", "replace_in_file", "append_file", "append_to_file", "move_file"} and result.ok and not result.dry_run:
            if path:
                self.modified_files.append(str(path))
            if data.get("dst"):
                self.modified_files.append(str(data["dst"]))
