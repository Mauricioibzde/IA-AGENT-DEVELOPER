"""Tool execution facade with read-before-edit enforcement and diff tracking."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Set, Tuple

from .config import AgentConfig
from .logging_config import AgentLogger
from .models import RiskLevel, ToolResult
from .tool_registry import ToolRegistry, infer_tool_call_from_text, parse_tool_calls

MUTATING_TOOLS = {
    "write_file", "create_file", "append_file", "append_to_file",
    "replace_in_file", "edit_file", "apply_patch", "move_file",
    "copy_file", "delete_file", "scaffold_project", "create_multiple_files",
    "create_directory",
}

READ_TOOLS = {"read_file", "read_file_range", "list_directory", "list_dir", "search_text",
              "search_files", "search_symbol", "get_file_info", "validate_path",
              "git_status", "git_diff", "git_log", "git_show", "git_branch", "git_changed_files"}


class Executor:
    def __init__(self, registry: ToolRegistry, config: AgentConfig, logger: AgentLogger) -> None:
        self.registry = registry
        self.config = config
        self.logger = logger
        self.modified_files: List[str] = []
        self.created_files: List[str] = []
        self.commands: List[str] = []
        self.read_files: Set[str] = set()
        self.step_diffs: List[str] = []

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

            # Track reads for read-before-edit enforcement.
            if name in READ_TOOLS:
                path = args.get("path") if isinstance(args, dict) else None
                if path:
                    self.read_files.add(str(path))

            started = time.time()
            result = self.registry.execute(
                name,
                args if isinstance(args, dict) else {},
                workspace=str(self.config.workspace),
                config=self.config,
            )
            duration_ms = int((time.time() - started) * 1000)
            self.logger.info(
                "tool_execution",
                message=f"{name} ok={result.ok}",
                tool=name,
                success=result.ok,
                duration_ms=duration_ms,
            )
            self._track(name, result)

            # Collect diff info for mutations.
            if name in MUTATING_TOOLS and result.ok and not result.dry_run:
                diff = result.data.get("diff")
                if diff:
                    self.step_diffs.append(diff)

            results.append({"tool": name, "result": result.to_dict()})
        return results, False

    def had_writes_this_step(self, results: List[Dict[str, Any]]) -> bool:
        """Return True if any tool in results mutated the filesystem."""
        for r in results:
            tool = r.get("tool", "")
            res = r.get("result", {})
            if tool in MUTATING_TOOLS and res.get("ok") and not res.get("dry_run"):
                return True
        return False

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
        if name in {"apply_patch", "replace_in_file", "edit_file", "append_file", "append_to_file", "move_file"} and result.ok and not result.dry_run:
            if path:
                self.modified_files.append(str(path))
            if data.get("dst"):
                self.modified_files.append(str(data["dst"]))
