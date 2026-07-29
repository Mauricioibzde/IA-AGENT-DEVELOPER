"""Prompt templates for planner/executor/reflector/report roles."""

from __future__ import annotations

import re
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

SENIOR_STANDARDS = """\
SENIOR ENGINEERING STANDARDS (always apply):
Identity: You are a senior full-stack engineer across frontend AND backend.
Languages you must handle well: JavaScript/TypeScript (React/Vite/Node), HTML/CSS,
Python (APIs, scripts, FastAPI/Flask patterns), Go, Rust, Java/Kotlin when present,
SQL, shell. Match the project's stack; do not force Python onto a frontend-only app.

Architecture & structure:
- Separate concerns (UI / domain / data / API). Prefer clear folders (src/, components/,
  api/, services/, tests/) over dumping everything in one file.
- Keep modules small and cohesive. Name files/functions by intent.
- Prefer composition over copy-paste. Extract shared helpers when duplication appears.
- Configuration via env/.env.example — never hardcode secrets, tokens, or passwords.

Frontend quality:
- Accessible HTML (semantic tags, labels, contrast, keyboard-friendly controls).
- Responsive layouts (mobile-first). Consistent spacing, typography, hierarchy.
- No broken imports, missing mounts, or dead placeholder stubs in production paths.
- React: proper components, keys in lists, controlled inputs when needed, CSS modules
  or dedicated CSS files. Always include package.json + vite.config + mounted root.
- Prefer polished, production-looking UI over lorem/demo junk.

Backend quality:
- Explicit input validation and clear error responses (status codes + messages).
- Idempotent-safe writes where relevant. Sensible logging without leaking secrets.
- REST/JSON APIs: consistent routes, CORS only when needed, health endpoint when useful.
- Persist data safely; avoid SQL injection / path traversal / command injection.
- Add smoke tests or compile/build checks for critical paths.

Security & reliability:
- Never write credentials into source. Use .env.example with placeholder values.
- Sanitize paths and user input. No shell interpolation of untrusted strings.
- Fail loudly with actionable errors; do not swallow exceptions silently.
- After edits: validate (tests, lint, build, compile) appropriate to the stack.

Code craft:
- Readable names, early returns, minimal nesting, no dead code.
- Comments only for non-obvious intent — never narrate obvious lines.
- Prefer edit_file/apply_patch for surgical changes; write_file for new files.
- Leave the project runnable/previewable when the goal is a web app."""

CORE_RULES = """\
RULES:
1. ALWAYS read a file before editing it. Never guess file contents.
2. Use relative paths only. Never escape the workspace.
3. After modifying a file, validate with the RIGHT stack command (tests/lint/build/compile).
4. If a tool fails, analyze the error and try a DIFFERENT approach.
5. Never repeat the exact same tool call that already failed.
6. Return only JSON tool calls. No prose explanations mixed in.
7. When the task is complete and validated, return the final tool.
8. For complex edits prefer edit_file or apply_patch over write_file.
9. Keep edits minimal and focused — change only what is needed for the goal.
10. If you need more context, read more files before deciding.
11. For web UI apps prefer React + Vite (scaffold_project template=react, path=".") or solid HTML/CSS.
12. Never leave a React app without package.json, vite.config, index.html, and a mounted main entry.
13. Apply SENIOR ENGINEERING STANDARDS: clean architecture, FE+BE quality, security, tests.
14. Choose validation by stack: Python→pytest/compileall; Node/React→npm test|build;
    Go→go test ./...; Rust→cargo check; Java→mvn/gradle test when present.
15. Do not invent dependencies you cannot install; prefer stdlib or already-listed deps."""


def system_prompt(workspace: str) -> str:
    return (
        "You are Forge's senior autonomous coding agent (local Ollama).\n"
        "You are a polyglot full-stack specialist: strong frontend AND backend.\n"
        "You plan, implement, validate, and self-correct like a senior engineer on a team.\n"
        f"Workspace root: {workspace}\n\n"
        f"{SENIOR_STANDARDS}\n\n"
        f"{CORE_RULES}\n"
    )


def planner_prompt(goal: str, project_summary: str, conversation: str = "") -> str:
    conversation_block = ""
    if conversation and conversation.strip():
        conversation_block = (
            "\nRecent chat context (the user may ask to APPLY these suggestions in code):\n"
            f"{conversation.strip()[:4500]}\n"
            "If the user goal is to implement/apply improvements from chat, plan concrete file edits "
            "based on that context — do not plan a generic explanation-only task.\n"
        )
    return (
        "You are the PLANNER for a senior full-stack coding agent.\n"
        "Do NOT modify files. Return ONLY a JSON object.\n\n"
        "Required JSON schema:\n"
        "{\n"
        '  "goal": "string — the user objective",\n'
        '  "summary": "string — brief strategy (architecture + stack choice)",\n'
        '  "risks": ["string — potential risks"],\n'
        '  "tasks": [\n'
        "    {\n"
        '      "id": "task-N",\n'
        '      "title": "short title",\n'
        '      "description": "what to do, senior practices to apply, and how to validate",\n'
        '      "dependencies": ["task-ids this depends on"],\n'
        '      "relevant_files": ["paths to read/modify"],\n'
        '      "validation_commands": ["commands to verify success"],\n'
        '      "risk_level": "low|medium|high"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Planning guidelines:\n"
        "- Start with a read/analysis task to understand existing code and stack.\n"
        "- Split large changes into small focused tasks (1-3 files each).\n"
        "- Each mutating task needs a stack-correct validation command.\n"
        "- Python: 'python -m compileall .' or 'python -m pytest -q'.\n"
        "- Node/React/Vite: prefer 'npm run build' (or 'npm test' / lint if present).\n"
        "- Go: 'go test ./...' ; Rust: 'cargo check' ; Java: project test command if present.\n"
        "- Do NOT use python compileall for frontend-only (HTML/CSS/JSX) goals.\n"
        "- New web apps: scaffold react (Vite) OR complete HTML/CSS landing — previewable UI.\n"
        "- APIs: include validation, clear errors, and a health/smoke check when useful.\n"
        "- Prefer maintainable structure (components/services/tests) over one giant file.\n"
        "- Include a final validation/review task.\n"
        "- Identify files via relevant_files.\n\n"
        f"User goal:\n{goal}\n"
        f"{conversation_block}\n"
        f"Project summary:\n{project_summary}\n"
    )


def executor_prompt(
    goal: str,
    task: Task,
    tools: ToolRegistry,
    context: str,
    *,
    workspace: str = "",
    previous_results: Optional[str] = None,
    recent_diffs: Optional[str] = None,
    no_progress: bool = False,
) -> str:
    parts = [
        "You are the EXECUTOR — a senior full-stack engineer. Return JSON tool call(s) ONLY.\n",
        f"Workspace root: {workspace}\n",
        f"\n{SENIOR_STANDARDS}\n",
        f"\n{CORE_RULES}\n",
        f"\nTool call examples:\n{TOOL_CALL_EXAMPLES}\n",
        f"\nAvailable tools:\n{tools.descriptions_for_prompt()}\n",
        f"\n## Overall goal\n{goal}\n",
        f"\n## Current task\nid={task.id} title={task.title}\n{task.description}\n",
    ]
    if task.notes:
        parts.append(f"\n## Task notes\n{task.notes}\n")
    if no_progress:
        parts.append(
            "\n## Warning\nYour last tool call repeated without progress. "
            "Use a DIFFERENT tool or different arguments.\n"
        )
    if previous_results:
        parts.append(f"\n## Previous tool results (same task — learn from these)\n{previous_results}\n")
    if recent_diffs:
        parts.append(f"\n## Recent diffs\n{recent_diffs}\n")
    parts.append(f"\n## Context\n{context}\n")
    parts.append(
        "\nThink step by step (senior bar):\n"
        "1. What files do I need? → read first\n"
        "2. What is the cleanest maintainable change?\n"
        "3. Frontend/backend concerns separated? Security ok?\n"
        "4. Validate with the correct stack command\n"
        "5. Done? → return final tool\n"
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
        "You are the REFLECTION agent for a senior coding workflow.\n"
        "Analyze results against correctness, maintainability, and validation.\n"
        "Return ONLY JSON with these keys:\n"
        "- status: continue | retry | replan | rollback | ask_user | finish | abort\n"
        "- analysis: what happened and why (be specific)\n"
        "- next_action: concrete next step description\n"
        "- relevant_files: files to focus on next\n"
        "- should_replan: true if the plan needs restructuring\n"
        "- risk_level: low | medium | high\n"
        "- evidence: specific error messages or output lines supporting your analysis\n\n"
        "Decision guidelines:\n"
        "- 'finish': tools succeeded AND validation passed AND result is production-quality enough for the goal\n"
        "- 'continue': partial progress, more tools needed for this task\n"
        "- 'retry': fixable error — describe a DIFFERENT fix approach\n"
        "- 'replan': task decomposition was wrong\n"
        "- 'rollback': changes made things worse\n"
        "- 'abort': unrecoverable after multiple attempts\n"
        "- Prefer retry/replan over finish if code is stubby, broken, insecure, or unvalidated\n\n"
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
        "Mention stack choices and validation briefly when relevant.\n"
        f"Goal: {goal}\nFacts:\n{facts}\n"
    )


def _goal_looks_frontend(goal: str) -> bool:
    g = goal.lower()
    return bool(
        re.search(
            r"\b(react|vite|html|css|landing|frontend|front-end|ui|ux|página|pagina|website|site|dashboard|javascript|\bjs\b|aplicativ)\b",
            g,
        )
    )


def _goal_looks_react(goal: str) -> bool:
    g = goal.lower()
    return bool(re.search(r"\b(react|vite|next\.?js|tsx|jsx|spa)\b", g))


def _goal_looks_plain_web(goal: str) -> bool:
    from .web_scaffold import looks_like_plain_web_goal

    return looks_like_plain_web_goal(goal)


def _goal_looks_backend(goal: str) -> bool:
    g = goal.lower()
    return bool(
        re.search(
            r"\b(api|backend|back-end|endpoint|fastapi|flask|express|django|server|rest|graphql|database|sql)\b",
            g,
        )
    )


def minimal_safe_plan(goal: str) -> dict:
    frontend = _goal_looks_frontend(goal)
    backend = _goal_looks_backend(goal)
    plain_web = _goal_looks_plain_web(goal)
    react = _goal_looks_react(goal)
    g = (goal or "").lower()
    # "Adicione uma seção na página" on an existing HTML app — treat as plain web edit.
    page_edit = bool(
        re.search(r"\b(se[cç][aã]o|section|página|pagina|layout|hero|rodapé|footer)\b", g)
    ) and not react

    if (plain_web or (page_edit and not backend)) and not backend:
        validate: list[str] = []
        editing = bool(re.search(r"\b(adicion|alter|edit|atualiz|inclu|melhor)\b", g)) or "index.html" in g
        execute_desc = (
            f"{goal}\n"
            + (
                "Edite a página estática existente (index.html + style.css + app.js). "
                "HTML semântico, CSS polido, JS mínimo. NÃO use React/Vite/npm. "
                "Não rode npm/pytest/python."
                if editing
                else "Crie/atualize uma app pequena estática: index.html + style.css + app.js. "
                "HTML semântico, CSS polido, JS mínimo funcional. NÃO use React/Vite/npm "
                "a menos que o usuário peça. Não rode npm run build."
            )
        )
        return {
            "goal": goal,
            "summary": "Plano rápido: app HTML/CSS/JS estática (fallback).",
            "risks": ["Model failed to produce a valid plan — using static web fallback"],
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Editar HTML/CSS/JS" if editing else "Criar app HTML/CSS/JS",
                    "description": execute_desc,
                    "dependencies": [],
                    "relevant_files": ["index.html", "style.css", "app.js"],
                    "validation_commands": validate,
                    "risk_level": "low",
                },
                {
                    "id": "task-2",
                    "title": "Revisar preview",
                    "description": (
                        "Garantir que index.html linka style.css e app.js, "
                        "e que a UI abre no preview sem erros óbvios."
                    ),
                    "dependencies": ["task-1"],
                    "relevant_files": ["index.html", "style.css", "app.js"],
                    "validation_commands": [],
                    "risk_level": "low",
                },
            ],
        }

    if frontend and not backend:
        validate = ["npm run build"] if react else []
        execute_desc = (
            f"{goal}\nApply senior frontend practices: semantic HTML/accessible UI or "
            "React+Vite with proper mount, polished layout, no stubs."
        )
    elif backend and not frontend:
        validate = ["python -m compileall ."]
        execute_desc = (
            f"{goal}\nApply senior backend practices: validation, clear errors, "
            "no secrets in code, smoke/health check when useful."
        )
    else:
        validate = []
        execute_desc = (
            f"{goal}\nApply senior full-stack practices for the detected stack; "
            "validate with the appropriate build/test command."
        )

    return {
        "goal": goal,
        "summary": "Plano mínimo seguro (fallback) com barra de qualidade sênior.",
        "risks": ["Model failed to produce a valid plan — using conservative fallback"],
        "tasks": [
            {
                "id": "task-1",
                "title": "Analisar estrutura e stack",
                "description": (
                    "Ler arquivos relevantes do workspace, detectar frontend/backend "
                    "e linguagens em uso antes de alterar código."
                ),
                "dependencies": [],
                "relevant_files": [],
                "validation_commands": [],
                "risk_level": "low",
            },
            {
                "id": "task-2",
                "title": "Implementar com qualidade sênior",
                "description": execute_desc,
                "dependencies": ["task-1"],
                "relevant_files": [],
                "validation_commands": list(validate),
                "risk_level": "medium",
            },
            {
                "id": "task-3",
                "title": "Validar resultado",
                "description": (
                    "Validar arquivos afetados com o comando correto da stack. "
                    "Garantir que o app/API fica executável e sem regressões óbvias."
                ),
                "dependencies": ["task-2"],
                "relevant_files": [],
                "validation_commands": list(validate),
                "risk_level": "low",
            },
        ],
    }
