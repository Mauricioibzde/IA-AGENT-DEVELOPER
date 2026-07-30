"""Project scaffolding and multi-file creation tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..config import AgentConfig
from ..models import RiskLevel, ToolDefinition, ToolResult
from ..security import atomic_write_text, resolve_in_workspace


def _scaffold_files(project_name: str, template: str) -> Dict[str, str]:
    template = (template or "node").lower().strip()
    if template in {"py", "python"}:
        return {
            "README.md": f"# {project_name}\n\nPython starter project.\n",
            "pyproject.toml": (
                f'[project]\nname = "{project_name}"\nversion = "0.1.0"\n'
                'requires-python = ">=3.10"\n'
            ),
            "src/main.py": (
                "def main() -> None:\n"
                '    print("Hello from starter project")\n\n\n'
                'if __name__ == "__main__":\n'
                "    main()\n"
            ),
            "tests/test_main.py": "def test_smoke():\n    assert True\n",
        }
    if template == "react":
        try:
            from ia_platform.project_templates import react_vite_files

            return react_vite_files(project_name)
        except Exception:
            # Offline / unit-test fallback — still a runnable Vite app shape.
            return {
                "README.md": f"# {project_name}\n\nReact + Vite starter.\n",
                "package.json": json.dumps(
                    {
                        "name": project_name,
                        "private": True,
                        "type": "module",
                        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                        "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
                        "devDependencies": {"@vitejs/plugin-react": "^4.3.4", "vite": "^5.4.11"},
                    },
                    indent=2,
                )
                + "\n",
                "vite.config.js": (
                    'import { defineConfig } from "vite";\n'
                    'import react from "@vitejs/plugin-react";\n\n'
                    "export default defineConfig({\n"
                    "  plugins: [react()],\n"
                    '  server: { host: "127.0.0.1", port: Number(process.env.PORT) || 5173 },\n'
                    "});\n"
                ),
                "index.html": (
                    "<!doctype html>\n<html lang=\"pt-BR\">\n  <head>\n"
                    '    <meta charset="UTF-8" />\n'
                    f"    <title>{project_name}</title>\n  </head>\n  <body>\n"
                    '    <div id="root"></div>\n'
                    '    <script type="module" src="/src/main.jsx"></script>\n'
                    "  </body>\n</html>\n"
                ),
                "src/main.jsx": (
                    'import React from "react";\n'
                    'import { createRoot } from "react-dom/client";\n'
                    'import App from "./App.jsx";\n'
                    'import "./index.css";\n\n'
                    'createRoot(document.getElementById("root")).render(<App />);\n'
                ),
                "src/App.jsx": (
                    'export default function App() {\n'
                    "  return <main><h1>Hello from starter project</h1></main>;\n"
                    "}\n"
                ),
                "src/index.css": "* { box-sizing: border-box; margin: 0; }\n",
            }
    return {
        "README.md": f"# {project_name}\n",
        "package.json": json.dumps(
            {
                "name": project_name,
                "version": "1.0.0",
                "private": True,
                "scripts": {"start": "node index.js", "test": "node -e \"console.log('ok')\""},
            },
            indent=2,
        )
        + "\n",
        "index.js": "console.log('Hello from starter project');\n",
    }


def scaffold_project(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = context["workspace"]
    cfg: AgentConfig = context["config"]
    project_name = str(args.get("name", "project"))
    template = str(args.get("template", "node"))
    # Default path="." scaffolds into the current workspace (Forge project folder).
    # An explicit path (including one equal to the project name) creates a subdirectory.
    raw_path = args.get("path")
    if raw_path is None or str(raw_path).strip() in {"", "."}:
        target_dir = Path(workspace)
    else:
        target_dir = resolve_in_workspace(workspace, str(raw_path).strip())
    files = _scaffold_files(project_name, template)
    if cfg.dry_run:
        return ToolResult(
            ok=True,
            dry_run=True,
            data={
                "action": "scaffold_project",
                "path": str(target_dir),
                "files": list(files.keys()),
                "template": template,
            },
        )
    target_dir.mkdir(parents=True, exist_ok=True)
    created: List[str] = []
    for rel, content in files.items():
        file_path = resolve_in_workspace(target_dir, rel)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(file_path, content)
        created.append(str(file_path))
    return ToolResult(ok=True, data={"path": str(target_dir), "files": created, "template": template})


def create_multiple_files(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = context["workspace"]
    cfg: AgentConfig = context["config"]
    created: List[str] = []
    planned: List[str] = []
    for entry in args.get("files", []) or []:
        path = entry.get("path") if isinstance(entry, dict) else None
        if not path:
            continue
        file_path = resolve_in_workspace(workspace, path)
        planned.append(str(file_path))
        if cfg.dry_run:
            continue
        file_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(file_path, str(entry.get("content", "")))
        created.append(str(file_path))
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "create_multiple_files", "files": planned})
    return ToolResult(ok=True, data={"files": created})


def final_tool(args: Dict[str, Any], **_context: Any) -> ToolResult:
    return ToolResult(ok=True, data={"answer": args.get("answer", "")})


def build_project_tools() -> List[ToolDefinition]:
    return [
        ToolDefinition(
            name="scaffold_project",
            description=(
                "Create a starter project (node|python|react). Prefer react for web UIs (Vite+React). "
                "Use path='.' to scaffold into the current workspace root; any other path creates a subdirectory."
            ),
            argument_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "path": {"type": "string"},
                    "template": {"type": "string"},
                },
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=scaffold_project,
        ),
        ToolDefinition(
            name="create_multiple_files",
            description="Create several files in one call",
            argument_schema={"type": "object", "properties": {"files": {"type": "array"}}, "required": ["files"]},
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=create_multiple_files,
        ),
        ToolDefinition(
            name="final",
            description="Finish with a final answer",
            argument_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=final_tool,
        ),
    ]
