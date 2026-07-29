"""Lexical search tools over the workspace."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ..models import RiskLevel, ToolDefinition, ToolResult
from ..security import is_probably_binary, resolve_in_workspace

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".agent",
}


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        yield path


def search_files(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = Path(context["workspace"]).resolve()
    query = str(args.get("query", args.get("name", ""))).strip()
    extension = args.get("extension")
    matches: List[str] = []
    for path in _iter_files(workspace):
        rel = str(path.relative_to(workspace)).replace("\\", "/")
        if extension and path.suffix.lstrip(".") != str(extension).lstrip("."):
            continue
        if query and query.lower() not in rel.lower() and query.lower() not in path.name.lower():
            continue
        matches.append(rel)
        if len(matches) >= int(args.get("limit", 100)):
            break
    return ToolResult(ok=True, data={"matches": matches, "count": len(matches)})


def search_text(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = Path(context["workspace"]).resolve()
    pattern = str(args.get("pattern", ""))
    use_regex = bool(args.get("regex", False))
    limit = int(args.get("limit", 50))
    if not pattern:
        return ToolResult(ok=False, error="pattern is required")
    regex = re.compile(pattern if use_regex else re.escape(pattern))
    hits: List[Dict[str, Any]] = []
    for path in _iter_files(workspace):
        if is_probably_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(
                    {
                        "path": str(path.relative_to(workspace)).replace("\\", "/"),
                        "line": lineno,
                        "text": line[:240],
                    }
                )
                if len(hits) >= limit:
                    return ToolResult(ok=True, data={"matches": hits, "count": len(hits)})
    return ToolResult(ok=True, data={"matches": hits, "count": len(hits)})


def search_symbol(args: Dict[str, Any], **context: Any) -> ToolResult:
    symbol = str(args.get("symbol", "")).strip()
    if not symbol:
        return ToolResult(ok=False, error="symbol is required")
    # Reuse text search for def/class/function-like patterns.
    pattern = rf"\b(def|class|function|const|let|var)\s+{re.escape(symbol)}\b"
    return search_text({"pattern": pattern, "regex": True, "limit": args.get("limit", 50)}, **context)


def build_search_tools() -> List[ToolDefinition]:
    return [
        ToolDefinition(
            name="search_files",
            description="Search files by name/extension",
            argument_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "name": {"type": "string"},
                    "extension": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=search_files,
        ),
        ToolDefinition(
            name="search_text",
            description="Search file contents by text or regex",
            argument_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "regex": {"type": "boolean"},
                    "limit": {"type": "integer"},
                },
                "required": ["pattern"],
            },
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=search_text,
        ),
        ToolDefinition(
            name="search_symbol",
            description="Search for definitions of a symbol",
            argument_schema={
                "type": "object",
                "properties": {"symbol": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["symbol"],
            },
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=search_symbol,
        ),
    ]
