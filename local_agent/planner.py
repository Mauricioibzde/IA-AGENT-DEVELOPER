"""Planner: produce structured task plans from user goals."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .models import Plan, RiskLevel, Task, TaskStatus
from .ollama_client import OllamaClient
from .project_index import ProjectIndex
from .prompts import minimal_safe_plan, planner_prompt


class Planner:
    def __init__(self, client: OllamaClient, model: str) -> None:
        self.client = client
        self.model = model

    def create_plan(
        self,
        goal: str,
        project_summary: str,
        *,
        index: Optional[ProjectIndex] = None,
    ) -> Plan:
        prompt = planner_prompt(goal, project_summary)
        try:
            raw = self.client.complete(prompt, model=self.model, temperature=0.1)
            data = self._parse_plan_json(raw)
            if data is None:
                repair = self.client.complete(
                    "Your previous output was not valid JSON. Fix it and return ONLY the plan JSON:\n" + raw[:3000],
                    model=self.model,
                    temperature=0,
                )
                data = self._parse_plan_json(repair)
            if data is None:
                data = minimal_safe_plan(goal)
        except Exception:
            data = minimal_safe_plan(goal)

        plan = self._to_plan(data, fallback_goal=goal)

        # Post-process: auto-discover relevant_files if the planner left them empty.
        if index:
            self._enrich_with_index(plan, index, goal)

        # Ensure at least one validation command per mutating task.
        self._ensure_validation_commands(plan, index)

        return plan

    def update_plan(self, plan: Plan, error: str) -> Plan:
        prompt = (
            "Update this JSON plan after the error. Return ONLY JSON plan.\n"
            f"Error: {error}\nCurrent plan:\n{json.dumps(self._plan_to_dict(plan), ensure_ascii=False)}"
        )
        try:
            raw = self.client.complete(prompt, model=self.model, temperature=0.1)
            data = self._parse_plan_json(raw) or self._plan_to_dict(plan)
        except Exception:
            data = self._plan_to_dict(plan)
        updated = self._to_plan(data, fallback_goal=plan.goal)
        done = {t.id: t for t in plan.tasks if t.status == TaskStatus.COMPLETED}
        for task in updated.tasks:
            if task.id in done:
                task.status = TaskStatus.COMPLETED
                task.attempts = done[task.id].attempts
        return updated

    def _enrich_with_index(self, plan: Plan, index: ProjectIndex, goal: str) -> None:
        """Add relevant_files from the project index when the model left them empty."""
        goal_lower = goal.lower()
        searched = [f.path for f in index.search_relevant(goal, limit=6)]
        for task in plan.tasks:
            if task.relevant_files:
                continue
            desc_lower = task.description.lower()
            candidates = list(searched)
            for f in index.files:
                name = f.path.rsplit("/", 1)[-1].lower()
                if name in desc_lower or name in goal_lower:
                    candidates.append(f.path)
                elif any(sym.lower() in desc_lower for sym in f.symbols[:10]):
                    candidates.append(f.path)
            task.relevant_files = list(dict.fromkeys(candidates))[:5]

    def _ensure_validation_commands(self, plan: Plan, index: Optional[ProjectIndex] = None) -> None:
        """Ensure mutating tasks have project-aware validation commands."""
        mutate_words = ["create", "write", "edit", "modify", "refactor", "fix", "add", "remove", "delete", "implement"]
        for task in plan.tasks:
            if task.validation_commands:
                continue
            desc_lower = task.description.lower()
            if not any(word in desc_lower for word in mutate_words):
                continue

            cmds: List[str] = []
            if index:
                for key in ("test", "lint", "build"):
                    detected = index.detected_commands.get(key) or []
                    if detected:
                        cmds.append(detected[0])
                        break
                if not cmds and index.package_scripts:
                    if "test" in index.package_scripts:
                        cmds.append("npm test")
                    elif "lint" in index.package_scripts:
                        cmds.append("npm run lint")
                    elif "build" in index.package_scripts:
                        cmds.append("npm run build")

            if not cmds and index:
                has_python = any(f.language == "python" for f in index.files)
                has_node = bool(index.package_scripts) or any(
                    f.language in {"javascript", "typescript"} for f in index.files
                )
                if has_python and not has_node:
                    cmds = ["python -m compileall ."]

            if not cmds and index:
                has_python = any(f.language == "python" for f in index.files)
                if has_python and not index.package_scripts:
                    cmds = ["python -m compileall ."]

            task.validation_commands = cmds
            if not cmds:
                continue
            if "test" in desc_lower or "validate" in desc_lower:
                if index and index.detected_commands.get("test"):
                    extra = index.detected_commands["test"][0]
                    if extra not in task.validation_commands:
                        task.validation_commands.append(extra)
                elif "python -m pytest -q --tb=short" not in task.validation_commands:
                    task.validation_commands.append("python -m pytest -q --tb=short")

    def _parse_plan_json(self, text: str) -> Optional[Dict[str, Any]]:
        content = text.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "tasks" in data:
                return data
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict) and "tasks" in data:
            return data
        return None

    def _to_plan(self, data: Dict[str, Any], fallback_goal: str) -> Plan:
        tasks_data = data.get("tasks") if isinstance(data.get("tasks"), list) else []
        tasks: List[Task] = []
        for index, item in enumerate(tasks_data):
            if not isinstance(item, dict):
                continue
            risk_raw = str(item.get("risk_level", "low")).lower()
            try:
                risk = RiskLevel(risk_raw)
            except ValueError:
                risk = RiskLevel.LOW
            tasks.append(
                Task(
                    id=str(item.get("id") or f"task-{index+1}"),
                    title=str(item.get("title") or f"Task {index+1}"),
                    description=str(item.get("description") or fallback_goal),
                    dependencies=[str(x) for x in item.get("dependencies") or []],
                    validation_commands=[str(x) for x in item.get("validation_commands") or []],
                    relevant_files=[str(x) for x in item.get("relevant_files") or []],
                    risk_level=risk,
                    status=TaskStatus.PENDING,
                )
            )
        if not tasks:
            safe = minimal_safe_plan(fallback_goal)
            return self._to_plan(safe, fallback_goal=fallback_goal)
        return Plan(
            goal=str(data.get("goal") or fallback_goal),
            summary=str(data.get("summary") or ""),
            tasks=tasks,
            risks=[str(r) for r in data.get("risks") or []],
        )

    @staticmethod
    def _plan_to_dict(plan: Plan) -> Dict[str, Any]:
        return {
            "goal": plan.goal,
            "summary": plan.summary,
            "risks": plan.risks,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "dependencies": t.dependencies,
                    "relevant_files": t.relevant_files,
                    "validation_commands": t.validation_commands,
                    "risk_level": t.risk_level.value,
                    "status": t.status.value,
                }
                for t in plan.tasks
            ],
        }
