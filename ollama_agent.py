import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not str(OLLAMA_URL).startswith(("http://", "https://")):
    OLLAMA_URL = f"http://{OLLAMA_URL}"


def call_model(prompt: str, model: str = "qwen3-coder:30b") -> str:
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
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.load(response)
    return data.get("response", "").strip()


def infer_tool_call_from_text(text: str) -> Dict[str, Any] | None:
    content = text.strip()
    lower = content.lower()

    if any(phrase in lower for phrase in ["starter project", "scaffold", "create a project", "create project"]):
        name_match = re.search(r"(?:named|called)\s+([a-z0-9_.-]+)", content, re.I)
        folder_match = re.search(r"folder\s+([a-z0-9_.-]+)", content, re.I)
        name = name_match.group(1) if name_match else "project"
        path = folder_match.group(1) if folder_match else name
        return {"tool": "scaffold_project", "args": {"name": name, "path": path}}

    if any(phrase in lower for phrase in ["create a file", "create file", "make file", "write file", "create a source file", "create source file"]):
        path_match = re.search(r"(?:named|called|file\s+)([a-z0-9_.\\/-]+)", content, re.I)
        path = path_match.group(1) if path_match else "file.txt"
        content_match = re.search(r"(?:with the content|content\s*[:=])\s*(.+?)(?:\.|$)", content, re.I)
        file_content = content_match.group(1).strip().strip('"\'') if content_match else ""
        return {"tool": "write_file", "args": {"path": path, "content": file_content}}

    if any(phrase in lower for phrase in ["validate", "confirm", "check that"]):
        return {"tool": "run_command", "args": {"command": "dir", "cwd": "."}}

    return None


def parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    content = text.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    try:
        payload = json.loads(content)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            if "tool_calls" in payload and isinstance(payload["tool_calls"], list):
                return [item for item in payload["tool_calls"] if isinstance(item, dict)]
            return [payload]
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, re.S)
    if match:
        try:
            payload = json.loads(match.group(0))
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                if "tool_calls" in payload and isinstance(payload["tool_calls"], list):
                    return [item for item in payload["tool_calls"] if isinstance(item, dict)]
                return [payload]
        except json.JSONDecodeError:
            pass

    return []


def execute_tool(tool_name: str, args: Dict[str, Any], workspace: str) -> Dict[str, Any]:
    if tool_name in {"write_file", "create_file"}:
        path = Path(args["path"])
        if not path.is_absolute():
            path = Path(workspace) / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.get("content", ""), encoding="utf-8")
        return {"ok": True, "path": str(path)}

    if tool_name in {"append_to_file", "append_file"}:
        path = Path(args["path"])
        if not path.is_absolute():
            path = Path(workspace) / path
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(existing + args.get("content", ""), encoding="utf-8")
        return {"ok": True, "path": str(path)}

    if tool_name in {"replace_in_file", "edit_file"}:
        path = Path(args["path"])
        if not path.is_absolute():
            path = Path(workspace) / path
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        original = path.read_text(encoding="utf-8")
        updated = original.replace(args.get("old", ""), args.get("new", ""))
        path.write_text(updated, encoding="utf-8")
        return {"ok": True, "path": str(path)}

    if tool_name == "create_directory":
        path = Path(args["path"])
        if not path.is_absolute():
            path = Path(workspace) / path
        path.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(path)}

    if tool_name == "read_file":
        path = Path(args["path"])
        if not path.is_absolute():
            path = Path(workspace) / path
        return {"ok": True, "content": path.read_text(encoding="utf-8")}

    if tool_name == "list_dir":
        path = Path(args.get("path", workspace))
        if not path.is_absolute():
            path = Path(workspace) / path
        return {"ok": True, "items": [p.name for p in path.iterdir()]}

    if tool_name == "run_command":
        command = args.get("command", "")
        cwd = Path(args.get("cwd", workspace))
        if not cwd.is_absolute():
            cwd = Path(workspace) / cwd
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    if tool_name == "scaffold_project":
        project_name = args.get("name", "project")
        target_dir = Path(args.get("path", project_name))
        if not target_dir.is_absolute():
            target_dir = Path(workspace) / target_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "README.md").write_text(f"# {project_name}\n", encoding="utf-8")
        (target_dir / "package.json").write_text(
            json.dumps(
                {
                    "name": project_name,
                    "version": "1.0.0",
                    "private": True,
                    "scripts": {"start": "node index.js", "test": "node -e \"console.log('ok')\""},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (target_dir / "index.js").write_text("console.log('Hello from starter project');\n", encoding="utf-8")
        return {"ok": True, "path": str(target_dir)}

    if tool_name == "final":
        return {"ok": True, "answer": args.get("answer", "")}

    raise ValueError(f"Unsupported tool: {tool_name}")


def run_agent(prompt: str, workspace: str, model: str = "qwen3-coder:30b", max_steps: int = 5) -> str:
    workspace_path = Path(workspace).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    instruction = (
        "You are a professional local coding agent with tools.\n"
        "Work step by step and use tools when necessary.\n"
        "Use these schemas:\n"
        '- create a file: {"tool":"write_file","args":{"path":"relative/path.txt","content":"text"}}\n'
        '- append to a file: {"tool":"append_to_file","args":{"path":"relative/path.txt","content":"text"}}\n'
        '- replace text in a file: {"tool":"replace_in_file","args":{"path":"relative/path.txt","old":"old text","new":"new text"}}\n'
        '- run a shell command: {"tool":"run_command","args":{"command":"cmd here","cwd":"."}}\n'
        '- scaffold a project: {"tool":"scaffold_project","args":{"name":"my-app","path":"relative/path"}}\n'
        '- create a source file: {"tool":"write_file","args":{"path":"relative/src/file.js","content":"// code\n"}}\n'
        'After running a validation command, report the result clearly: success or failure, exit code, and relevant output.\n'
        "For multiple tool calls, return a JSON array of objects.\n"
        'If you are done, return {"tool":"final","args":{"answer":"your final response"}}.\n'
        'Prefer using tools for file and command operations.\n'
        'If the request involves creating a project or a folder with starter files, use the scaffold_project tool directly.\n'
        'If the request involves several files, create them one by one.\n'
        'If a validation or command fails, immediately try one corrective action and report the outcome clearly.\n'
        'Do not explain the tool format; just return the JSON tool call(s).\n'
        f"Workspace root: {workspace_path}\n"
    )

    history: List[str] = []
    current_prompt = prompt

    for step in range(max_steps):
        full_prompt = instruction + "\nUser request: " + current_prompt + "\n\nConversation history:\n" + "\n".join(history[-8:])
        response = call_model(full_prompt, model=model)
        if not response:
            return "Ollama returned an empty response."

        tool_calls = parse_tool_calls(response)
        if not tool_calls:
            inferred = infer_tool_call_from_text(response)
            if inferred is not None:
                tool_calls = [inferred]
            else:
                if step == 0:
                    return response
                return response

        results = []
        for call in tool_calls:
            tool_name = call.get("tool")
            if not tool_name:
                continue
            if tool_name == "final":
                return call.get("args", {}).get("answer", "")
            try:
                tool_result = execute_tool(tool_name, call.get("args", {}), str(workspace_path))
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
    parser.add_argument("--model", default="qwen3-coder:30b", help="Ollama model name")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum tool iterations")
    args = parser.parse_args()

    print(run_agent(args.prompt, args.workspace, model=args.model, max_steps=args.max_steps))


if __name__ == "__main__":
    main()
