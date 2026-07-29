"""Tool execution facade with read-before-edit enforcement and diff tracking."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Set, Tuple

from .config import AgentConfig
from .logging_config import AgentLogger
from .models import RiskLevel, ToolResult
from .security import to_rel_path
from .tool_registry import ToolRegistry, infer_tool_call_from_text, parse_tool_calls

MUTATING_TOOLS = {
    "write_file", "create_file", "append_file", "append_to_file",
    "replace_in_file", "edit_file", "apply_patch", "move_file",
    "copy_file", "delete_file", "scaffold_project", "create_multiple_files",
    "create_directory",
}

READ_TOOLS = {"read_file", "read_file_range", "list_directory", "list_dir", "search_text",
              "search_files", "search_symbol", "search_relevant", "get_file_info", "validate_path",
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

    def _rel(self, path: str | None) -> str:
        return to_rel_path(self.config.workspace, path)

    def mark_read(self, path: str) -> None:
        if path:
            self.read_files.add(self._rel(path))

    def mark_reads(self, paths: List[str]) -> None:
        for path in paths:
            self.mark_read(path)

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
                    self.read_files.add(self._rel(str(path)))

            # Enforce read-before-edit on existing files.
            if name in MUTATING_TOOLS:
                path = args.get("path") if isinstance(args, dict) else None
                if path:
                    rel = self._rel(str(path))
                    abs_path = self.config.workspace / rel
                    already_known = rel in self.read_files or rel in self.created_files
                    if abs_path.exists() and not already_known:
                        result = ToolResult(
                            ok=False,
                            error=f"Must read_file '{rel}' before editing. Read the file first, then retry.",
                        )
                        results.append({"tool": name, "result": result.to_dict()})
                        continue

            if name in MUTATING_TOOLS and not self.config.dry_run:
                new_paths = self._mutation_new_paths(name, args if isinstance(args, dict) else {})
                already = set(self.modified_files + self.created_files)
                projected = already | new_paths
                if len(projected) > self.config.max_modified_files:
                    result = ToolResult(
                        ok=False,
                        error=(
                            f"Modified file budget exceeded ({self.config.max_modified_files}). "
                            "Finish or validate current changes."
                        ),
                    )
                    results.append({"tool": name, "result": result.to_dict()})
                    continue

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
            self._track(name, result, args if isinstance(args, dict) else {})

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

    def _mutation_new_paths(self, name: str, args: Dict[str, Any]) -> Set[str]:
        """Paths this mutation would newly count against the file budget."""
        already = set(self.modified_files + self.created_files)
        candidates: Set[str] = set()

        def add(raw: str | None) -> None:
            if not raw:
                return
            rel = self._rel(str(raw))
            if rel and rel not in already:
                candidates.add(rel)

        if name in {"write_file", "create_file", "create_directory", "append_file", "append_to_file",
                    "replace_in_file", "edit_file", "apply_patch"}:
            add(str(args.get("path") or ""))
        elif name == "create_multiple_files":
            files = args.get("files")
            if isinstance(files, list):
                for entry in files:
                    if isinstance(entry, dict):
                        add(str(entry.get("path") or ""))
                    elif isinstance(entry, str):
                        add(entry)
        elif name == "scaffold_project":
            add(str(args.get("path") or "."))
        elif name == "move_file":
            add(str(args.get("path") or args.get("src") or ""))
            add(str(args.get("dst") or ""))
        elif name == "copy_file":
            add(str(args.get("dst") or ""))
        elif name == "delete_file":
            add(str(args.get("path") or ""))
        return candidates

    def _track(self, name: str, result: ToolResult, args: Dict[str, Any]) -> None:
        data = result.data
        if name == "run_command" and data.get("command"):
            self.commands.append(str(data["command"]))
        if not result.ok or result.dry_run:
            return

        def _add_created(raw: str | None) -> None:
            if not raw:
                return
            rel = self._rel(raw)
            self.created_files.append(rel)
            self.read_files.add(rel)  # newly written files are known content

        def _add_modified(raw: str | None) -> None:
            if not raw:
                return
            rel = self._rel(raw)
            self.modified_files.append(rel)
            self.read_files.add(rel)

        if name in {"write_file", "create_file", "create_directory"}:
            _add_created(str(data.get("path") or args.get("path") or ""))
        elif name == "create_multiple_files":
            files = data.get("files")
            if isinstance(files, list):
                for item in files:
                    _add_created(str(item))
            elif isinstance(args.get("files"), list):
                for entry in args["files"]:
                    if isinstance(entry, dict) and entry.get("path"):
                        _add_created(str(entry["path"]))
        elif name == "scaffold_project":
            files = data.get("files")
            if isinstance(files, list):
                for item in files:
                    _add_created(str(item))
            # Also mark common scaffold roots as known.
            base = self._rel(str(data.get("path") or args.get("path") or "."))
            if base and base != ".":
                self.created_files.append(base)
        elif name in {"apply_patch", "replace_in_file", "edit_file", "append_file", "append_to_file"}:
            _add_modified(str(data.get("path") or args.get("path") or ""))
        elif name == "move_file":
            _add_modified(str(data.get("path") or args.get("path") or args.get("src") or ""))
            if data.get("dst") or args.get("dst"):
                _add_modified(str(data.get("dst") or args.get("dst")))
        elif name == "copy_file":
            _add_created(str(data.get("dst") or args.get("dst") or ""))
        elif name == "delete_file":
            _add_modified(str(data.get("path") or args.get("path") or ""))
