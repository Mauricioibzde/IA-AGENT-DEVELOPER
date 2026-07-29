"""Prompt templates for planner/executor/reflector/report roles."""

from __future__ import annotations

from typing import List

from .models import Task
from .tool_registry import ToolRegistry


def system_prompt(workspace: str) -> str:
    return (
        "You are a professional local coding agent.\n"
        "Stay inside the workspace. Never invent tool results.\n"
        "Read before editing. Validate after changes.\n"
        "Prefer structured JSON tool calls.\n"
        f"Workspace root: {workspace}\n"
    )


def planner_prompt(goal: str, project_summary: str) -> str:
    return (
        "You are the planner. Do not modify files. Create a JSON plan only.\n"
        "Return ONLY JSON with keys: goal, summary, tasks.\n"
        "Each task needs: id, title, description, dependencies, relevant_files, "
        "validation_commands, risk_level (low|medium|high).\n"
        "Split work into small steps. Identify risks.\n\n"
        f"User goal:\n{goal}\n\nProject summary:\n{project_summary}\n"
    )


def executor_prompt(goal: str, task: Task, tools: ToolRegistry, context: str) -> str:
    return (
        f"{system_prompt('')}"
        "You are the executor for one task. Return JSON tool call(s) only.\n"
        "You may return one object, an array, or {\"tool_calls\":[...]}.\n"
        "When finished with the overall user goal, return "
        '{"tool":"final","args":{"answer":"..."}}.\n'
        f"Available tools:\n{tools.descriptions_for_prompt()}\n\n"
        f"Overall goal: {goal}\n"
        f"Current task id={task.id} title={task.title}\n"
        f"Task description: {task.description}\n"
        f"Relevant context:\n{context}\n"
    )


def reflector_prompt(
    task: Task,
    tool_results: str,
    validation_summary: str,
    previous_attempts: int,
) -> str:
    return (
        "You are the reflection agent. Return ONLY JSON with keys: "
        "status, analysis, next_action, relevant_files, should_replan, risk_level, evidence.\n"
        "status must be one of: continue, retry, replan, rollback, ask_user, finish, abort.\n"
        "Be concrete. Do not repeat a failing action unchanged.\n\n"
        f"Task: {task.id} {task.title}\nDescription: {task.description}\n"
        f"Attempts: {previous_attempts}/{task.max_attempts}\n"
        f"Tool results:\n{tool_results}\n"
        f"Validation:\n{validation_summary}\n"
    )


def final_report_prompt(goal: str, facts: str) -> str:
    return (
        "Write a concise final engineering report in Portuguese or English "
        "matching the user's language. Use the provided facts only.\n"
        f"Goal: {goal}\nFacts:\n{facts}\n"
    )


def minimal_safe_plan(goal: str) -> dict:
    return {
        "goal": goal,
        "summary": "Plano mínimo seguro gerado localmente após falha de JSON do modelo.",
        "tasks": [
            {
                "id": "task-1",
                "title": "Analisar estrutura",
                "description": "Inspecionar arquivos relevantes do workspace",
                "dependencies": [],
                "relevant_files": [],
                "validation_commands": [],
                "risk_level": "low",
            },
            {
                "id": "task-2",
                "title": "Executar solicitação",
                "description": goal,
                "dependencies": ["task-1"],
                "relevant_files": [],
                "validation_commands": [],
                "risk_level": "medium",
            },
            {
                "id": "task-3",
                "title": "Validar resultado",
                "description": "Validar arquivos/comandos afetados",
                "dependencies": ["task-2"],
                "relevant_files": [],
                "validation_commands": [],
                "risk_level": "low",
            },
        ],
    }
