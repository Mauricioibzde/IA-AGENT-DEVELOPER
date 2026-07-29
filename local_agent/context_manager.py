"""Context assembly with per-section budgets."""

from __future__ import annotations

from typing import List, Optional

from .config import AgentConfig
from .memory import AgentMemory
from .models import Task
from .project_index import ProjectIndex


class ContextManager:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

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
    ) -> str:
        sections = {
            "goal": self._clip(goal, 1500),
            "task": self._clip(f"{task.id}: {task.title}\n{task.description}", 1500),
            "project": self._clip(project_index.summary(limit=25), 4000),
            "memory": self._clip(memory.relevant_summary(), 2500),
            "files": self._clip(self._file_snippets(project_index, task, extra_files or []), 8000),
            "errors": self._clip("\n".join(errors or []) or "(none)", 2000),
            "validation": self._clip(validation or "(none)", 2000),
        }
        parts = [f"## {name}\n{body}" for name, body in sections.items()]
        joined = "\n\n".join(parts)
        return self._clip(joined, self.config.max_context_chars)

    def _file_snippets(self, index: ProjectIndex, task: Task, extra: List[str]) -> str:
        wanted = list(dict.fromkeys([*task.relevant_files, *extra]))
        chunks: List[str] = []
        for rel in wanted[:12]:
            matches = index.find_by_name(rel) or [type("X", (), {"path": rel, "symbols": []})()]
            path = self.config.workspace / matches[0].path
            if not path.exists() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            lines = text.splitlines()
            snippet = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines[:80]))
            truncated = len(lines) > 80
            chunks.append(
                f"FILE {matches[0].path} truncated={truncated}\n{snippet}"
            )
        return "\n\n".join(chunks) if chunks else "(no file snippets)"

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 20)] + "\n...[truncated]..."
