"""Prompt templates for planner/executor/reflector/report roles."""

from __future__ import annotations

from typing import List, Optional

from .models import Task
from .tool_registry import ToolRegistry


TOOL_CALL_EXAMPLES = """\
Single call:
{"tool":"read_file","args":{"path":"src/main.py"}}

Multiple calls (array):
[{"tool":"read_file","args":{"path":"src/main.py"}},{"tool":"list_directory","args":{"path":"src"}}]

Edit a file safely:
{"tool":"edit_file","args":{"path":"src/main.py","line":10,"old":"print('old')","new":"print('new')"}}

Apply a patch:
{"tool":"apply_patch","args":{"path":"src/main.py","hunks":[{"old":"def foo():\\n    pass","new":"def foo():\\n    return 42"}]}}

Finish:
{"tool":"final","args":{"answer":"Done. Created src/main.py with the API handler."}}"""

CORE_RULES = """\
RULES:
1. ALWAYS read a file before editing it. Never guess file contents.
2. Use relative paths only. Never escape the workspace.
3. After modifying a file, validate (run tests, lint, or compileall).
4. If a tool fails, analyze the error and try a DIFFERENT approach.
5. Never repeat the exact same tool call that already failed.
6. Return only JSON tool calls. No prose explanations mixed in.
7. When the task is complete and validated, return the final tool.
8. For complex edits prefer edit_file or apply_patch over write_file.
9. Keep edits minimal and focused — change only what is needed.
10. If you need more context, read more files before deciding."""


def system_prompt(workspace: str) -> str:
    return (
        "You are an expert autonomous coding agent operating locally via Ollama.\n"
        "You analyze code, plan changes, execute tools, validate results, and self-correct.\n"
        f"Workspace root: {workspace}\n\n"
        f"{CORE_RULES}\n"
    )


def planner_prompt(goal: str, project_summary: str) -> str:
    return (
        "You are the PLANNER. Your job is to create a structured execution plan.\n"
        "Do NOT modify files. Return ONLY a JSON object.\n\n"
        "Required JSON schema:\n"
        "{\n"
        '  "goal": "string — the user objective",\n'
        '  "summary": "string — brief strategy description",\n'
        '  "risks": ["string — potential risks"],\n'
        '  "tasks": [\n'
        "    {\n"
        '      "id": "task-N",\n'
        '      "title": "short title",\n'
        '      "description": "what to do and how to validate",\n'
        '      "dependencies": ["task-ids this depends on"],\n'
        '      "relevant_files": ["paths to read/modify"],\n'
        '      "validation_commands": ["commands to verify success"],\n'
        '      "risk_level": "low|medium|high"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Planning guidelines:\n"
        "- Start with a read/analysis task to understand existing code.\n"
        "- Split large changes into small focused tasks (1-3 files each).\n"
        "- Each task should have at least one validation command.\n"
        "- For Python projects: use 'python -m compileall .' or 'python -m pytest -q'.\n"
        "- For Node projects: use 'npm test' or 'npm run lint'.\n"
        "- Mark dependencies so tasks run in the right order.\n"
        "- Include a final validation/review task.\n"
        "- Identify files that will likely need reading via relevant_files.\n\n"
        f"User goal:\n{goal}\n\n"
        f"Project summary:\n{project_summary}\n"
    )


def executor_prompt(
    goal: str,
    task: Task,
    tools: ToolRegistry,
    context: str,
    *,
    previous_results: Optional[str] = None,
) -> str:
    parts = [
        system_prompt(""),
        "You are the EXECUTOR. Return JSON tool call(s) ONLY.\n",
        f"\n{CORE_RULES}\n",
        f"\nTool call examples:\n{TOOL_CALL_EXAMPLES}\n",
        f"\nAvailable tools:\n{tools.descriptions_for_prompt()}\n",
        f"\n## Overall goal\n{goal}\n",
        f"\n## Current task\nid={task.id} title={task.title}\n{task.description}\n",
    ]
    if previous_results:
        parts.append(f"\n## Previous tool results in this step\n{previous_results}\n")
    parts.append(f"\n## Context\n{context}\n")
    parts.append(
        "\nThink step by step:\n"
        "1. What information do I need? → read files first\n"
        "2. What is the minimal change? → edit only what's needed\n"
        "3. How do I validate? → run tests/compile after editing\n"
        "4. Am I done? → return final tool when validated\n"
        "\nReturn your tool call(s) now:\n"
    )
    return "".join(parts)


def reflector_prompt(
    task: Task,
    tool_results: str,
    validation_summary: str,
    previous_attempts: int,
) -> str:
    return (
        "You are the REFLECTION agent. Analyze the results and decide next action.\n"
        "Return ONLY JSON with these keys:\n"
        "- status: continue | retry | replan | rollback | ask_user | finish | abort\n"
        "- analysis: what happened and why (be specific)\n"
        "- next_action: concrete next step description\n"
        "- relevant_files: files to focus on next\n"
        "- should_replan: true if the plan needs restructuring\n"
        "- risk_level: low | medium | high\n"
        "- evidence: specific error messages or output lines supporting your analysis\n\n"
        "Decision guidelines:\n"
        "- 'finish': all tools succeeded AND validation passed\n"
        "- 'continue': partial progress, more tools needed for this task\n"
        "- 'retry': a fixable error occurred — describe a DIFFERENT fix approach\n"
        "- 'replan': the task decomposition was wrong, need new tasks\n"
        "- 'rollback': changes made things worse, restore backup\n"
        "- 'abort': unrecoverable error after multiple attempts\n\n"
        f"Task: {task.id} — {task.title}\n"
        f"Description: {task.description}\n"
        f"Attempts so far: {previous_attempts}/{task.max_attempts}\n\n"
        f"Tool results:\n{tool_results}\n\n"
        f"Validation results:\n{validation_summary}\n"
    )


def final_report_prompt(goal: str, facts: str) -> str:
    return (
        "Write a concise final engineering report matching the user's language.\n"
        "Use only the provided facts. Be honest about failures.\n"
        f"Goal: {goal}\nFacts:\n{facts}\n"
    )


def minimal_safe_plan(goal: str) -> dict:
    return {
        "goal": goal,
        "summary": "Plano mínimo seguro gerado localmente após falha de JSON do modelo.",
        "risks": ["Model failed to produce a valid plan — using conservative fallback"],
        "tasks": [
            {
                "id": "task-1",
                "title": "Analisar estrutura",
                "description": "Ler arquivos relevantes do workspace para entender a base de código",
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
                "validation_commands": ["python -m compileall ."],
                "risk_level": "medium",
            },
            {
                "id": "task-3",
                "title": "Validar resultado",
                "description": "Validar arquivos e comandos afetados. Verificar se testes passam.",
                "dependencies": ["task-2"],
                "relevant_files": [],
                "validation_commands": ["python -m compileall ."],
                "risk_level": "low",
            },
        ],
    }
