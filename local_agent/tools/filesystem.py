"""Line-targeted file editing, search, and filesystem tools."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

from ..config import AgentConfig
from ..models import RiskLevel, ToolDefinition, ToolResult
from ..security import WorkspaceSecurityError, atomic_write_text, is_probably_binary, resolve_in_workspace


def _ctx_workspace(context: Dict[str, Any]) -> Path:
    return Path(context["workspace"]).resolve()


def _cfg(context: Dict[str, Any]) -> AgentConfig:
    return context["config"]


def read_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    if not path.exists():
        return ToolResult(ok=False, error=f"File not found: {path}")
    if is_probably_binary(path):
        return ToolResult(ok=False, error=f"Refusing to read binary file: {path}")
    size = path.stat().st_size
    if size > cfg.read_file_max_bytes:
        return ToolResult(
            ok=False,
            error=f"File too large ({size} bytes). Use read_file_range or raise limit.",
            data={"path": str(path), "size": size},
        )
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    numbered = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))
    return ToolResult(ok=True, data={"path": str(path), "content": numbered, "size": size, "total_lines": len(lines)})


def read_file_range(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    start = max(1, int(args.get("start_line", 1)))
    end = int(args.get("end_line", start + 99))
    if end < start:
        return ToolResult(ok=False, error="end_line must be >= start_line")
    if not path.exists():
        return ToolResult(ok=False, error=f"File not found: {path}")
    if is_probably_binary(path):
        return ToolResult(ok=False, error=f"Refusing to read binary file: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    sliced = lines[start - 1 : end]
    numbered = "\n".join(f"{idx + start}: {line}" for idx, line in enumerate(sliced))
    return ToolResult(
        ok=True,
        data={
            "path": str(path),
            "start_line": start,
            "end_line": min(end, len(lines)),
            "total_lines": len(lines),
            "content": numbered,
            "truncated": end < len(lines) or start > 1,
        },
    )


def write_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    content = str(args.get("content", ""))
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "write_file", "path": str(path)})
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, content)
    return ToolResult(ok=True, data={"path": str(path), "size": len(content)})


def edit_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    """Line-targeted edit: replace old text with new at/near a specific line.

    If 'line' is given, the search for 'old' starts at that line for precision.
    If 'old' is empty but 'new' and 'line' are given, inserts new text after that line.
    """
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    if not path.exists():
        return ToolResult(ok=False, error=f"File not found: {path}")

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    old = str(args.get("old", ""))
    new = str(args.get("new", ""))
    target_line = int(args.get("line", 0))

    if not old and target_line > 0 and new:
        # Insert mode: insert new text after target_line.
        insert_idx = min(target_line, len(lines))
        new_text = new if new.endswith("\n") else new + "\n"
        lines.insert(insert_idx, new_text)
        updated = "".join(lines)
    elif old:
        if target_line > 0:
            # Search near the target line for more precision.
            window = 15
            start = max(0, target_line - window - 1)
            end = min(len(lines), target_line + window)
            region = "".join(lines[start:end])
            if old in region:
                count = region.count(old)
                if count > 1:
                    return ToolResult(ok=False, error=f"Ambiguous match near line {target_line}: {count} occurrences")
                before = "".join(lines[:start])
                after = "".join(lines[end:])
                updated = before + region.replace(old, new, 1) + after
            elif old in original:
                count = original.count(old)
                if count > 1:
                    return ToolResult(ok=False, error=f"Ambiguous match: {count} occurrences in file")
                updated = original.replace(old, new, 1)
            else:
                return ToolResult(ok=False, error=f"Text not found near line {target_line}")
        else:
            count = original.count(old)
            if count == 0:
                return ToolResult(ok=False, error="Text not found in file")
            if count > 1:
                return ToolResult(ok=False, error=f"Ambiguous match: {count} occurrences. Provide 'line' or more context.")
            updated = original.replace(old, new, 1)
    else:
        return ToolResult(ok=False, error="edit_file requires 'old' text or 'line' + 'new' for insertion")

    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "edit_file", "path": str(path)})

    # Backup and write.
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(original, encoding="utf-8")
    atomic_write_text(path, updated)

    # Compute simple diff summary.
    orig_lines = original.splitlines()
    new_lines = updated.splitlines()
    added = len(new_lines) - len(orig_lines)
    return ToolResult(
        ok=True,
        data={
            "path": str(path),
            "backup": str(backup),
            "lines_delta": added,
            "total_lines": len(new_lines),
        },
    )


def append_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    content = str(args.get("content", ""))
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "append_file", "path": str(path)})
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    atomic_write_text(path, existing + content)
    return ToolResult(ok=True, data={"path": str(path)})


def create_directory(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "create_directory", "path": str(path)})
    path.mkdir(parents=True, exist_ok=True)
    return ToolResult(ok=True, data={"path": str(path)})


def list_directory(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    path = resolve_in_workspace(workspace, args.get("path", "."))
    if not path.exists():
        return ToolResult(ok=False, error=f"Directory not found: {path}")
    if not path.is_dir():
        return ToolResult(ok=False, error=f"Not a directory: {path}")
    items = sorted(p.name for p in path.iterdir())
    return ToolResult(ok=True, data={"path": str(path), "items": items})


def delete_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "delete_file", "path": str(path)})
    if not path.exists():
        return ToolResult(ok=False, error=f"Path not found: {path}")
    if path.is_dir():
        return ToolResult(ok=False, error="delete_file refuses directories")
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_bytes(path.read_bytes())
    path.unlink()
    return ToolResult(ok=True, data={"path": str(path), "backup": str(backup)})


def move_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    src = resolve_in_workspace(workspace, args.get("src"))
    dst = resolve_in_workspace(workspace, args.get("dst"))
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "move_file", "src": str(src), "dst": str(dst)})
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return ToolResult(ok=True, data={"src": str(src), "dst": str(dst)})


def copy_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    src = resolve_in_workspace(workspace, args.get("src"))
    dst = resolve_in_workspace(workspace, args.get("dst"))
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "copy_file", "src": str(src), "dst": str(dst)})
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    return ToolResult(ok=True, data={"src": str(src), "dst": str(dst)})


def get_file_info(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    if not path.exists():
        return ToolResult(ok=False, error=f"Path not found: {path}")
    stat = path.stat()
    return ToolResult(
        ok=True,
        data={
            "path": str(path),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "size": stat.st_size,
            "binary": is_probably_binary(path) if path.is_file() else False,
        },
    )


def validate_path(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = _ctx_workspace(context)
    try:
        path = resolve_in_workspace(workspace, args.get("path", "."))
    except WorkspaceSecurityError as exc:
        return ToolResult(ok=False, error=str(exc))
    exists = path.exists()
    kind = "missing"
    items = None
    if path.is_file():
        kind = "file"
    elif path.is_dir():
        kind = "directory"
        items = sorted(p.name for p in path.iterdir())
    return ToolResult(ok=exists, data={"path": str(path), "kind": kind, "items": items})


def replace_in_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    """Legacy global text replace retained for compatibility."""
    workspace = _ctx_workspace(context)
    cfg = _cfg(context)
    path = resolve_in_workspace(workspace, args.get("path"))
    old = str(args.get("old", ""))
    new = str(args.get("new", ""))
    if not path.exists():
        return ToolResult(ok=False, error=f"File not found: {path}")
    if old == "":
        return ToolResult(ok=False, error="replace_in_file requires non-empty 'old'")
    original = path.read_text(encoding="utf-8")
    count = original.count(old)
    if count == 0:
        return ToolResult(ok=False, error=f"No matches for old text in {path}")
    if cfg.dry_run:
        return ToolResult(
            ok=True,
            dry_run=True,
            data={"action": "replace_in_file", "path": str(path), "replacements": count},
        )
    atomic_write_text(path, original.replace(old, new))
    return ToolResult(ok=True, data={"path": str(path), "replacements": count})


def build_filesystem_tools() -> List[ToolDefinition]:
    return [
        ToolDefinition(
            name="read_file",
            description="Read a UTF-8 text file with line numbers",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=read_file,
        ),
        ToolDefinition(
            name="read_file_range",
            description="Read specific line range from a file",
            argument_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
                "required": ["path"],
            },
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=read_file_range,
        ),
        ToolDefinition(
            name="write_file",
            description="Create or overwrite a file",
            argument_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path"],
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=write_file,
        ),
        ToolDefinition(
            name="edit_file",
            description="Precise line-targeted edit: replace 'old' with 'new' near 'line', or insert 'new' after 'line'",
            argument_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "line": {"type": "integer"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path"],
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=edit_file,
        ),
        ToolDefinition(
            name="append_file",
            description="Append text to a file",
            argument_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path"],
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=append_file,
        ),
        ToolDefinition(
            name="create_directory",
            description="Create a directory",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level=RiskLevel.LOW,
            mutating=True,
            requires_confirmation=False,
            handler=create_directory,
        ),
        ToolDefinition(
            name="list_directory",
            description="List directory entries",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=list_directory,
        ),
        ToolDefinition(
            name="delete_file",
            description="Delete a file with .bak backup",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level=RiskLevel.HIGH,
            mutating=True,
            requires_confirmation=True,
            handler=delete_file,
        ),
        ToolDefinition(
            name="move_file",
            description="Move/rename a file",
            argument_schema={
                "type": "object",
                "properties": {"src": {"type": "string"}, "dst": {"type": "string"}},
                "required": ["src", "dst"],
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=move_file,
        ),
        ToolDefinition(
            name="copy_file",
            description="Copy a file",
            argument_schema={
                "type": "object",
                "properties": {"src": {"type": "string"}, "dst": {"type": "string"}},
                "required": ["src", "dst"],
            },
            risk_level=RiskLevel.LOW,
            mutating=True,
            requires_confirmation=False,
            handler=copy_file,
        ),
        ToolDefinition(
            name="get_file_info",
            description="Get file metadata (size, type, binary)",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=get_file_info,
        ),
        ToolDefinition(
            name="validate_path",
            description="Check if a path exists and its type",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            mutating=False,
            requires_confirmation=False,
            handler=validate_path,
        ),
        ToolDefinition(
            name="replace_in_file",
            description="Legacy global text replace (prefer edit_file or apply_patch)",
            argument_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
                "required": ["path", "old", "new"],
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=replace_in_file,
        ),
        # Aliases
        ToolDefinition("create_file", "Alias for write_file", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path"]}, RiskLevel.MEDIUM, True, False, write_file),
        ToolDefinition("list_dir", "Alias for list_directory", {"type": "object", "properties": {"path": {"type": "string"}}}, RiskLevel.LOW, False, False, list_directory),
        ToolDefinition("append_to_file", "Alias for append_file", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path"]}, RiskLevel.MEDIUM, True, False, append_file),
        ToolDefinition("edit_file_insert", "Alias: insert text after a line number", {"type": "object", "properties": {"path": {"type": "string"}, "line": {"type": "integer"}, "new": {"type": "string"}}, "required": ["path", "line", "new"]}, RiskLevel.MEDIUM, True, False, edit_file),
    ]
