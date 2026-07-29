"""Tool registry with schema validation."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

from .models import RiskLevel, ToolDefinition, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def descriptions_for_prompt(self) -> str:
        lines = []
        for tool in self._tools.values():
            lines.append(
                f"- {tool.name}: {tool.description} "
                f"(risk={tool.risk_level.value}, mutating={tool.mutating}) "
                f"schema={json.dumps(tool.argument_schema, ensure_ascii=False)}"
            )
        return "\n".join(lines)

    def validate_args(self, tool: ToolDefinition, args: Dict[str, Any]) -> Dict[str, Any]:
        schema = tool.argument_schema or {}
        properties = schema.get("properties", {}) if isinstance(schema.get("properties"), dict) else {}
        required = schema.get("required", []) if isinstance(schema.get("required"), list) else []
        if not isinstance(args, dict):
            raise ValueError("Tool args must be an object")
        missing = [key for key in required if key not in args]
        if missing:
            raise ValueError(f"Missing required args for {tool.name}: {missing}")
        validated: Dict[str, Any] = {}
        for key, value in args.items():
            if properties and key not in properties:
                # Allow unknown keys lightly, but keep them.
                validated[key] = value
                continue
            prop = properties.get(key, {}) if isinstance(properties, dict) else {}
            expected = prop.get("type") if isinstance(prop, dict) else None
            if expected == "string" and not isinstance(value, str):
                raise ValueError(f"Arg {key} must be string")
            if expected == "integer" and not isinstance(value, int):
                raise ValueError(f"Arg {key} must be integer")
            if expected == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Arg {key} must be number")
            if expected == "boolean" and not isinstance(value, bool):
                raise ValueError(f"Arg {key} must be boolean")
            if expected == "array" and not isinstance(value, list):
                raise ValueError(f"Arg {key} must be array")
            if expected == "object" and not isinstance(value, dict):
                raise ValueError(f"Arg {key} must be object")
            validated[key] = value
        return validated

    def execute(self, name: str, args: Dict[str, Any], **context: Any) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"Unsupported tool: {name}")
        try:
            validated = self.validate_args(tool, args or {})
            return tool.handler(validated, **context)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, error=str(exc))


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


def infer_tool_call_from_text(text: str) -> Dict[str, Any] | None:
    content = text.strip()
    lower = content.lower()

    scaffold_phrases = [
        "starter project", "scaffold", "create a project", "create project",
        "criar um projeto", "criar projeto", "gerar um projeto",
    ]
    if any(p in lower for p in scaffold_phrases):
        name_match = re.search(r"(?:named|called|nomeado|chamado|chamada|nome)\s+([a-z0-9_.-]+)", content, re.I)
        folder_match = re.search(r"(?:folder|pasta|diretorio|diretório)\s+([a-z0-9_.-]+)", content, re.I)
        template_match = re.search(r"\b(python|node|nodejs|react)\b", lower)
        name = name_match.group(1) if name_match else "project"
        path = folder_match.group(1) if folder_match else name
        template = "node"
        if template_match:
            token = template_match.group(1)
            template = "python" if token == "python" else ("react" if token == "react" else "node")
        return {"tool": "scaffold_project", "args": {"name": name, "path": path, "template": template}}

    write_phrases = [
        "create a file", "create file", "make file", "write file", "create a source file",
        "criar um arquivo", "criar arquivo", "escrever arquivo", "gerar arquivo",
    ]
    if any(p in lower for p in write_phrases):
        path_match = re.search(r"(?:named|called|chamado|chamada|nomeado)\s+([a-z0-9_.\\/-]+)", content, re.I)
        if not path_match:
            path_match = re.search(r"(?:file|arquivo)\s+([a-z0-9_.\\/-]+)", content, re.I)
        path = path_match.group(1) if path_match else "file.txt"
        content_match = re.search(
            r"(?:with the content|content\s*[:=]|com o conteudo|com o conteúdo|conteudo\s*[:=]|conteúdo\s*[:=])\s*(.+?)(?:\.|$)",
            content,
            re.I,
        )
        file_content = content_match.group(1).strip().strip("\"'") if content_match else ""
        return {"tool": "write_file", "args": {"path": path, "content": file_content}}

    dir_phrases = [
        "create a folder", "create folder", "make folder", "make directory", "create directory",
        "criar uma pasta", "criar pasta", "criar diretorio", "criar diretório",
    ]
    if any(p in lower for p in dir_phrases):
        path_match = re.search(r"(?:named|called|chamado|chamada|nomeado)\s+([a-z0-9_.\\/-]+)", content, re.I)
        if not path_match:
            path_match = re.search(r"(?:folder|pasta|diretorio|diretório)\s+([a-z0-9_.\\/-]+)", content, re.I)
        path = path_match.group(1) if path_match else "new-folder"
        return {"tool": "create_directory", "args": {"path": path}}

    if any(p in lower for p in ["list files", "show files", "list directory", "listar arquivos", "listar pasta"]):
        return {"tool": "list_directory", "args": {"path": "."}}

    if any(p in lower for p in ["read file", "open file", "ler arquivo", "abrir arquivo"]):
        path_match = re.search(r"(?:named|called|chamado|chamada|nomeado)\s+([a-z0-9_.\\/-]+)", content, re.I)
        if not path_match:
            path_match = re.search(r"(?:file|arquivo)\s+([a-z0-9_.\\/-]+)", content, re.I)
        path = path_match.group(1) if path_match else "README.md"
        return {"tool": "read_file", "args": {"path": path}}

    if any(p in lower for p in ["validate", "confirm", "check that", "validar", "verificar", "checar"]):
        path_match = re.search(
            r"(?:folder|pasta|directory|diretorio|diretório|in|em)\s+([a-z0-9_.\\/-]+)",
            content,
            re.I,
        )
        path = path_match.group(1) if path_match else "."
        return {"tool": "validate_path", "args": {"path": path}}

    return None


def register_many(registry: ToolRegistry, tools: Iterable[ToolDefinition]) -> None:
    for tool in tools:
        registry.register(tool)
