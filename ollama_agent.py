#!/usr/bin/env python3
"""Local Ollama coding agent with sandboxed tool execution."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not str(OLLAMA_URL).startswith(("http://", "https://")):
    OLLAMA_URL = f"http://{OLLAMA_URL}"

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3-coder:30b")

# Characters that usually require a real shell instead of argv execution.
SHELL_REQUIRED_CHARS = set("&|;<>*(){}[]$`\\")


class WorkspaceSecurityError(ValueError):
    """Raised when a tool tries to escape the workspace sandbox."""


class DryRunResult(dict):
    """Marker result used when --dry-run skips side effects."""


def resolve_in_workspace(workspace: str | Path, raw_path: str | Path | None, default: str = ".") -> Path:
    """Resolve a path and ensure it stays inside the workspace root."""
    workspace_root = Path(workspace).resolve()
    candidate = Path(default if raw_path in (None, "") else raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace_root / candidate).resolve()
    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise WorkspaceSecurityError(
            f"Path escapes workspace: {raw_path!r} -> {resolved} (workspace={workspace_root})"
        ) from exc
    return resolved


def call_model(prompt: str, model: str = DEFAULT_MODEL, verbose: bool = False) -> str:
    """Call Ollama chat API, falling back to generate if needed."""
    chat_payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(chat_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as response:
            data = json.load(response)
        message = data.get("message") or {}
        content = (message.get("content") or data.get("response") or "").strip()
        if content:
            if verbose:
                print(f"[llm/chat] {len(content)} chars", file=sys.stderr)
            return content
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        if verbose:
            print(f"[llm/chat] fallback to generate: {exc}", file=sys.stderr)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.load(response)
    content = data.get("response", "").strip()
    if verbose:
        print(f"[llm/generate] {len(content)} chars", file=sys.stderr)
    return content


def infer_tool_call_from_text(text: str) -> Dict[str, Any] | None:
    """Best-effort English/Portuguese heuristic when the model returns prose."""
    content = text.strip()
    lower = content.lower()

    scaffold_phrases = [
        "starter project",
        "scaffold",
        "create a project",
        "create project",
        "criar um projeto",
        "criar projeto",
        "gerar um projeto",
        "scaffolding",
    ]
    if any(phrase in lower for phrase in scaffold_phrases):
        name_match = re.search(
            r"(?:named|called|nomeado|chamado|chamada|nome)\s+([a-z0-9_.-]+)",
            content,
            re.I,
        )
        folder_match = re.search(
            r"(?:folder|pasta|diretorio|diretório)\s+([a-z0-9_.-]+)",
            content,
            re.I,
        )
        template_match = re.search(r"\b(python|node|nodejs|react)\b", lower)
        name = name_match.group(1) if name_match else "project"
        path = folder_match.group(1) if folder_match else name
        template = "python" if template_match and "python" in template_match.group(1) else "node"
        if template_match and template_match.group(1) in {"node", "nodejs"}:
            template = "node"
        if template_match and template_match.group(1) == "react":
            template = "react"
        return {"tool": "scaffold_project", "args": {"name": name, "path": path, "template": template}}

    write_phrases = [
        "create a file",
        "create file",
        "make file",
        "write file",
        "create a source file",
        "create source file",
        "criar um arquivo",
        "criar arquivo",
        "escrever arquivo",
        "gerar arquivo",
    ]
    if any(phrase in lower for phrase in write_phrases):
        path_match = re.search(
            r"(?:named|called|chamado|chamada|nomeado)\s+([a-z0-9_.\\/-]+)",
            content,
            re.I,
        )
        if not path_match:
            path_match = re.search(
                r"(?:file|arquivo)\s+([a-z0-9_.\\/-]+)",
                content,
                re.I,
            )
        path = path_match.group(1) if path_match else "file.txt"
        content_match = re.search(
            r"(?:with the content|content\s*[:=]|com o conteudo|com o conteúdo|conteudo\s*[:=]|conteúdo\s*[:=])\s*(.+?)(?:\.|$)",
            content,
            re.I,
        )
        file_content = content_match.group(1).strip().strip("\"'") if content_match else ""
        return {"tool": "write_file", "args": {"path": path, "content": file_content}}

    dir_phrases = [
        "create a folder",
        "create folder",
        "make folder",
        "make directory",
        "create directory",
        "criar uma pasta",
        "criar pasta",
        "criar diretorio",
        "criar diretório",
    ]
    if any(phrase in lower for phrase in dir_phrases):
        path_match = re.search(
            r"(?:named|called|chamado|chamada|nomeado)\s+([a-z0-9_.\\/-]+)",
            content,
            re.I,
        )
        if not path_match:
            path_match = re.search(
                r"(?:folder|pasta|diretorio|diretório)\s+([a-z0-9_.\\/-]+)",
                content,
                re.I,
            )
        path = path_match.group(1) if path_match else "new-folder"
        return {"tool": "create_directory", "args": {"path": path}}

    list_phrases = [
        "list files",
        "show files",
        "list directory",
        "show directory",
        "listar arquivos",
        "listar pasta",
        "mostrar arquivos",
    ]
    if any(phrase in lower for phrase in list_phrases):
        return {"tool": "list_dir", "args": {"path": "."}}

    read_phrases = [
        "read file",
        "open file",
        "show content",
        "ler arquivo",
        "abrir arquivo",
        "mostrar conteudo",
        "mostrar conteúdo",
    ]
    if any(phrase in lower for phrase in read_phrases):
        path_match = re.search(
            r"(?:named|called|chamado|chamada|nomeado)\s+([a-z0-9_.\\/-]+)",
            content,
            re.I,
        )
        if not path_match:
            path_match = re.search(
                r"(?:file|arquivo)\s+([a-z0-9_.\\/-]+)",
                content,
                re.I,
            )
        path = path_match.group(1) if path_match else "README.md"
        return {"tool": "read_file", "args": {"path": path}}

    validate_phrases = ["validate", "confirm", "check that", "validar", "verificar", "checar"]
    if any(phrase in lower for phrase in validate_phrases):
        path_match = re.search(
            r"(?:folder|pasta|directory|diretorio|diretório|in|em)\s+([a-z0-9_.\\/-]+)",
            content,
            re.I,
        )
        path = path_match.group(1) if path_match else "."
        return {"tool": "validate_path", "args": {"path": path}}

    return None


def parse_tool_call(payload: str | Dict[str, Any] | Any) -> tuple[str | None, Dict[str, Any]]:
    if isinstance(payload, dict):
        tool_name = payload.get("tool") or payload.get("name") or payload.get("action")
        args = payload.get("args", {})
        if isinstance(args, dict):
            return tool_name, args
        return tool_name, {}

    if isinstance(payload, str):
        content = payload.strip()
        if not content:
            return None, {}
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if not match:
                return None, {}
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None, {}
        return parse_tool_call(parsed)

    return None, {}


def parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    content = text.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    def _from_payload(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            parsed: List[Dict[str, Any]] = []
            for item in payload:
                tool_name, args = parse_tool_call(item)
                if tool_name:
                    parsed.append({"tool": tool_name, "args": args})
            return parsed
        if isinstance(payload, dict):
            if "tool_calls" in payload and isinstance(payload["tool_calls"], list):
                parsed = []
                for item in payload["tool_calls"]:
                    tool_name, args = parse_tool_call(item)
                    if tool_name:
                        parsed.append({"tool": tool_name, "args": args})
                return parsed
            tool_name, args = parse_tool_call(payload)
            if tool_name:
                return [{"tool": tool_name, "args": args}]
        return []

    try:
        payload = json.loads(content)
        parsed = _from_payload(payload)
        if parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\[.*\]|\{.*\})", content, re.S)
    if match:
        try:
            payload = json.loads(match.group(0))
            return _from_payload(payload)
        except json.JSONDecodeError:
            pass

    return []


def _maybe_shell(command: str) -> tuple[Any, bool]:
    """Prefer argv list when the command does not clearly need a shell."""
    if any(ch in command for ch in SHELL_REQUIRED_CHARS) or "&&" in command or "||" in command:
        return command, True
    try:
        return shlex.split(command, posix=os.name != "nt"), False
    except ValueError:
        return command, True


def _scaffold_files(project_name: str, template: str) -> Dict[str, str]:
    template = (template or "node").lower().strip()
    if template in {"py", "python"}:
        return {
            "README.md": f"# {project_name}\n\nPython starter project.\n",
            "pyproject.toml": (
                f'[project]\nname = "{project_name}"\nversion = "0.1.0"\n'
                'requires-python = ">=3.10"\n'
            ),
            "src/main.py": 'def main() -> None:\n    print("Hello from starter project")\n\n\nif __name__ == "__main__":\n    main()\n',
            "tests/test_main.py": "def test_smoke():\n    assert True\n",
        }
    if template == "react":
        return {
            "README.md": f"# {project_name}\n\nMinimal React/Vite-style starter placeholder.\n",
            "package.json": json.dumps(
                {
                    "name": project_name,
                    "version": "1.0.0",
                    "private": True,
                    "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                },
                indent=2,
            )
            + "\n",
            "index.html": (
                "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <meta charset=\"UTF-8\" />\n"
                f"    <title>{project_name}</title>\n  </head>\n  <body>\n"
                "    <div id=\"root\"></div>\n    <script type=\"module\" src=\"/src/main.jsx\"></script>\n"
                "  </body>\n</html>\n"
            ),
            "src/main.jsx": (
                "export function App() {\n  return <h1>Hello from starter project</h1>;\n}\n\n"
                "const root = document.getElementById('root');\n"
                "root.textContent = 'Hello from starter project';\n"
            ),
        }
    # default node
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


def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    workspace: str,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    if verbose:
        print(f"[tool] {tool_name} {json.dumps(args, ensure_ascii=False)}", file=sys.stderr)

    if tool_name in {"write_file", "create_file"}:
        path = resolve_in_workspace(workspace, args["path"])
        if dry_run:
            return {"ok": True, "dry_run": True, "action": "write_file", "path": str(path)}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.get("content", ""), encoding="utf-8")
        return {"ok": True, "path": str(path)}

    if tool_name in {"append_to_file", "append_file"}:
        path = resolve_in_workspace(workspace, args["path"])
        if dry_run:
            return {"ok": True, "dry_run": True, "action": "append_to_file", "path": str(path)}
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(existing + args.get("content", ""), encoding="utf-8")
        return {"ok": True, "path": str(path)}

    if tool_name in {"replace_in_file", "edit_file"}:
        path = resolve_in_workspace(workspace, args["path"])
        old = args.get("old", "")
        new = args.get("new", "")
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        original = path.read_text(encoding="utf-8")
        if old == "":
            raise ValueError("replace_in_file requires a non-empty 'old' string")
        count = original.count(old)
        if count == 0:
            raise ValueError(f"No matches for old text in {path}")
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "action": "replace_in_file",
                "path": str(path),
                "replacements": count,
            }
        updated = original.replace(old, new)
        path.write_text(updated, encoding="utf-8")
        return {"ok": True, "path": str(path), "replacements": count}

    if tool_name == "create_directory":
        path = resolve_in_workspace(workspace, args["path"])
        if dry_run:
            return {"ok": True, "dry_run": True, "action": "create_directory", "path": str(path)}
        path.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(path)}

    if tool_name == "read_file":
        path = resolve_in_workspace(workspace, args["path"])
        return {"ok": True, "content": path.read_text(encoding="utf-8")}

    if tool_name == "list_dir":
        path = resolve_in_workspace(workspace, args.get("path", "."))
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        return {"ok": True, "items": sorted(p.name for p in path.iterdir())}

    if tool_name == "validate_path":
        path = resolve_in_workspace(workspace, args.get("path", "."))
        exists = path.exists()
        kind = "missing"
        items: Optional[List[str]] = None
        if path.is_file():
            kind = "file"
        elif path.is_dir():
            kind = "directory"
            items = sorted(p.name for p in path.iterdir())
        return {"ok": exists, "path": str(path), "kind": kind, "items": items}

    if tool_name == "run_command":
        command = str(args.get("command", "")).strip()
        if not command:
            raise ValueError("run_command requires a non-empty command")
        cwd = resolve_in_workspace(workspace, args.get("cwd", "."))
        if dry_run:
            return {"ok": True, "dry_run": True, "action": "run_command", "command": command, "cwd": str(cwd)}
        argv, use_shell = _maybe_shell(command)
        completed = subprocess.run(
            argv,
            shell=use_shell,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=int(args.get("timeout", 60)),
        )
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "shell": use_shell,
        }

    if tool_name == "scaffold_project":
        project_name = args.get("name", "project")
        template = args.get("template", "node")
        target_dir = resolve_in_workspace(workspace, args.get("path", project_name))
        files = _scaffold_files(str(project_name), str(template))
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "action": "scaffold_project",
                "path": str(target_dir),
                "files": list(files.keys()),
                "template": template,
            }
        target_dir.mkdir(parents=True, exist_ok=True)
        created = []
        for rel, content in files.items():
            file_path = resolve_in_workspace(target_dir, rel)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            created.append(str(file_path))
        return {"ok": True, "path": str(target_dir), "files": created, "template": template}

    if tool_name == "create_multiple_files":
        created = []
        planned = []
        for entry in args.get("files", []):
            path = entry.get("path")
            if not path:
                continue
            file_path = resolve_in_workspace(workspace, path)
            planned.append(str(file_path))
            if dry_run:
                continue
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(entry.get("content", ""), encoding="utf-8")
            created.append(str(file_path))
        if dry_run:
            return {"ok": True, "dry_run": True, "action": "create_multiple_files", "files": planned}
        return {"ok": True, "files": created}

    if tool_name == "final":
        return {"ok": True, "answer": args.get("answer", "")}

    raise ValueError(f"Unsupported tool: {tool_name}")


def build_instruction(workspace_path: Path) -> str:
    return (
        "You are a professional local coding agent with tools.\n"
        "Work step by step and use tools when necessary.\n"
        "Use these schemas:\n"
        '- create a file: {"tool":"write_file","args":{"path":"relative/path.txt","content":"text"}}\n'
        '- append to a file: {"tool":"append_to_file","args":{"path":"relative/path.txt","content":"text"}}\n'
        '- replace text in a file: {"tool":"replace_in_file","args":{"path":"relative/path.txt","old":"old text","new":"new text"}}\n'
        '- run a shell command: {"tool":"run_command","args":{"command":"cmd here","cwd":"."}}\n'
        '- scaffold a project: {"tool":"scaffold_project","args":{"name":"my-app","path":"relative/path","template":"node|python|react"}}\n'
        '- create multiple files: {"tool":"create_multiple_files","args":{"files":[{"path":"relative/file1.txt","content":"hello"},{"path":"relative/file2.txt","content":"world"}]}}\n'
        '- list directory: {"tool":"list_dir","args":{"path":"."}}\n'
        '- validate path: {"tool":"validate_path","args":{"path":"relative/or/folder"}}\n'
        '- create a source file: {"tool":"write_file","args":{"path":"relative/src/file.js","content":"// code\\n"}}\n'
        "After running a validation command, report the result clearly: success or failure, exit code, and relevant output.\n"
        "For multiple tool calls, prefer create_multiple_files or a JSON array of objects.\n"
        'If you are done, return {"tool":"final","args":{"answer":"your final response"}}.\n'
        "Prefer using tools for file and command operations.\n"
        "If the request involves creating a project or a folder with starter files, use the scaffold_project tool directly.\n"
        "If a validation or command fails, immediately try one corrective action and report the outcome clearly.\n"
        "Do not explain the tool format; just return the JSON tool call(s).\n"
        "Stay inside the workspace. Use relative paths only.\n"
        f"Workspace root: {workspace_path}\n"
    )


def run_agent(
    prompt: str,
    workspace: str,
    model: str = DEFAULT_MODEL,
    max_steps: int = 5,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> str:
    workspace_path = Path(workspace).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    instruction = build_instruction(workspace_path)
    history: List[str] = []
    current_prompt = prompt

    for step in range(max_steps):
        full_prompt = (
            instruction
            + "\nUser request: "
            + current_prompt
            + "\n\nConversation history:\n"
            + "\n".join(history[-8:])
        )
        response = call_model(full_prompt, model=model, verbose=verbose)
        if not response:
            return "Ollama returned an empty response."

        tool_calls = parse_tool_calls(response)
        if not tool_calls:
            inferred = infer_tool_call_from_text(response)
            if inferred is not None:
                tool_calls = [inferred]
            else:
                return response

        results = []
        for call in tool_calls:
            tool_name = call.get("tool")
            if not tool_name:
                continue
            if tool_name == "final":
                return call.get("args", {}).get("answer", "")
            try:
                tool_result = execute_tool(
                    tool_name,
                    call.get("args", {}),
                    str(workspace_path),
                    dry_run=dry_run,
                    verbose=verbose,
                )
            except Exception as exc:
                tool_result = {"ok": False, "error": str(exc)}
            results.append({"tool": tool_name, "result": tool_result})
            history.append(f"Step {step + 1}: {tool_name} -> {json.dumps(tool_result, ensure_ascii=False)}")

        if not results:
            return response

        current_prompt = current_prompt + "\n\nTool results:\n" + json.dumps(results, ensure_ascii=False)
        if any(r.get("result", {}).get("ok") is False for r in results):
            current_prompt += "\n\nPlease try a corrective step to fix the failure."

    return "Agent reached the maximum number of steps without a final answer."


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a tool-using Ollama agent")
    parser.add_argument("prompt", help="Task to perform")
    parser.add_argument("--workspace", default=os.getcwd(), help="Workspace root")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum tool iterations")
    parser.add_argument("--dry-run", action="store_true", help="Plan tool actions without writing disk or running commands")
    parser.add_argument("--verbose", action="store_true", help="Print tool and LLM diagnostics to stderr")
    args = parser.parse_args()

    print(
        run_agent(
            args.prompt,
            args.workspace,
            model=args.model,
            max_steps=args.max_steps,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
