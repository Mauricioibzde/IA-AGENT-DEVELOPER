"""Context assembly with per-section budgets and auto file reading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import AgentConfig
from .memory import AgentMemory
from .models import Task
from .project_index import ProjectIndex
from .security import is_probably_binary


class ContextManager:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self._file_cache: Dict[str, str] = {}
        self.last_read_paths: List[str] = []

    def invalidate(self, path: str) -> None:
        rel = path.replace("\\", "/")
        abs_path = (self.config.workspace / rel).resolve()
        self._file_cache.pop(str(abs_path), None)
        self._file_cache.pop(rel, None)

    def invalidate_many(self, paths: List[str]) -> None:
        for path in paths:
            self.invalidate(path)

    def build(
        self,
        *,
        goal: str,
        task: Task,
        project_index: ProjectIndex,
        memory: AgentMemory,
        extra_files: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        validation: str = "",
        conversation: str = "",
        previous_results: Optional[str] = None,
    ) -> str:
        sections = {
            "goal": self._clip(goal, 1500),
            "conversation": self._clip(conversation, 2500) if conversation else "",
            "task": self._clip(
                f"id={task.id} title={task.title}\n{task.description}"
                + (f"\nNotes: {task.notes}" if task.notes else ""),
                1500,
            ),
            "project_map": self._clip(project_index.summary(limit=20), 3000),
            "memory": self._clip(memory.relevant_summary(), 2000),
            "relevant_files": self._clip(
                self._auto_read_files(project_index, task, extra_files or []),
                10000,
            ),
            "errors": self._clip(self._format_errors(errors), 2500),
            "validation": self._clip(validation or "(none)", 2000),
        }
        if previous_results:
            sections["previous_results"] = self._clip(previous_results, 3000)

        parts = [f"## {name}\n{body}" for name, body in sections.items() if body and body != "(none)"]
        joined = "\n\n".join(parts)
        return self._clip(joined, self.config.max_context_chars)

    def read_file_for_context(self, path: Path, max_lines: int = 120) -> Optional[str]:
        """Read a file with line numbers for inclusion in context."""
        abs_path = path if path.is_absolute() else self.config.workspace / path
        if not abs_path.exists() or not abs_path.is_file():
            return None
        if is_probably_binary(abs_path):
            return f"(binary file: {path})"
        if abs_path.stat().st_size > self.config.read_file_max_bytes:
            return f"(file too large: {abs_path.stat().st_size} bytes)"

        cache_key = str(abs_path)
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]

        try:
            text = abs_path.read_text(encoding="utf-8")
        except Exception:
            return None

        lines = text.splitlines()
        if len(lines) <= max_lines:
            numbered = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))
            result = f"FILE: {path} ({len(lines)} lines)\n{numbered}"
        else:
            head = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines[:60]))
            tail = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines[-30:], start=len(lines) - 29))
            result = (
                f"FILE: {path} ({len(lines)} lines, showing first 60 + last 30)\n"
                f"{head}\n...[lines {61}-{len(lines)-30} omitted]...\n{tail}"
            )
        self._file_cache[cache_key] = result
        return result

    def _auto_read_files(self, index: ProjectIndex, task: Task, extra: List[str]) -> str:
        """Automatically read relevant files for the context."""
        wanted = list(dict.fromkeys([*task.relevant_files, *extra]))

        # Also auto-discover likely relevant files from task description.
        if not wanted:
            desc_lower = task.description.lower()
            for f in index.files:
                if f.path.lower() in desc_lower or f.path.rsplit("/", 1)[-1].lower() in desc_lower:
                    wanted.append(f.path)
                if len(wanted) >= 8:
                    break

        # If still nothing, include key config/entry files.
        if not wanted:
            for f in index.files:
                if f.is_config or f.path in {"README.md", "setup.py", "main.py", "app.py", "index.js"}:
                    wanted.append(f.path)
                if len(wanted) >= 5:
                    break

        chunks: List[str] = []
        self.last_read_paths = []
        for rel in wanted[:15]:
            snippet = self.read_file_for_context(Path(rel))
            if snippet:
                chunks.append(snippet)
                self.last_read_paths.append(rel)

        return "\n\n".join(chunks) if chunks else "(no file snippets — use read_file tool to inspect files)"

    def _format_errors(self, errors: Optional[List[str]]) -> str:
        if not errors:
            return "(none)"
        formatted = []
        for i, err in enumerate(errors[-5:], 1):
            formatted.append(f"Error {i}: {err[:500]}")
        return "\n".join(formatted)

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 20)] + "\n...[truncated]..."
