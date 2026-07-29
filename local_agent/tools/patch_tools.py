"""Safe structured patch / unified-diff application."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..config import AgentConfig
from ..models import RiskLevel, ToolDefinition, ToolResult
from ..security import atomic_write_text, resolve_in_workspace


class PatchError(ValueError):
    pass


def _apply_structured_hunks(original: str, hunks: List[Dict[str, Any]]) -> str:
    """Apply hunks with unique context matching.

    Each hunk: {"old": "...", "new": "..."} and old must appear exactly once.
    """
    content = original
    for index, hunk in enumerate(hunks):
        old = hunk.get("old")
        new = hunk.get("new")
        if not isinstance(old, str) or not isinstance(new, str):
            raise PatchError(f"Hunk {index} requires string old/new")
        if old == "":
            raise PatchError(f"Hunk {index} has empty old context")
        count = content.count(old)
        if count == 0:
            raise PatchError(f"Hunk {index} context not found")
        if count > 1:
            raise PatchError(f"Hunk {index} is ambiguous ({count} matches)")
        content = content.replace(old, new, 1)
    return content


def _parse_unified_diff(diff_text: str) -> List[Dict[str, str]]:
    """Very small unified-diff to single-file old/new block extractor.

    Supports simple hunks where contiguous '-' lines are replaced by '+' lines.
    """
    lines = diff_text.splitlines()
    hunks: List[Dict[str, str]] = []
    old_buf: List[str] = []
    new_buf: List[str] = []

    def flush() -> None:
        nonlocal old_buf, new_buf
        if old_buf or new_buf:
            hunks.append({"old": "\n".join(old_buf), "new": "\n".join(new_buf)})
            old_buf, new_buf = [], []

    for line in lines:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            flush()
            continue
        if line.startswith("-"):
            old_buf.append(line[1:])
            continue
        if line.startswith("+"):
            new_buf.append(line[1:])
            continue
        # context line ends current replacement block
        flush()
    flush()
    if not hunks:
        raise PatchError("No applicable hunks found in unified diff")
    return hunks


def apply_patch(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = context["workspace"]
    cfg: AgentConfig = context["config"]
    path = resolve_in_workspace(workspace, args.get("path"))
    if not path.exists():
        return ToolResult(ok=False, error=f"File not found: {path}")

    original = path.read_text(encoding="utf-8")
    hunks = args.get("hunks")
    diff_text = args.get("diff")
    try:
        if isinstance(hunks, list) and hunks:
            updated = _apply_structured_hunks(original, hunks)
        elif isinstance(diff_text, str) and diff_text.strip():
            parsed = _parse_unified_diff(diff_text)
            updated = _apply_structured_hunks(original, parsed)
        else:
            return ToolResult(ok=False, error="apply_patch requires 'hunks' or 'diff'")
    except PatchError as exc:
        return ToolResult(ok=False, error=str(exc))

    before_after = list(
        difflib.unified_diff(
            original.splitlines(),
            updated.splitlines(),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
            lineterm="",
        )
    )
    if cfg.dry_run:
        return ToolResult(
            ok=True,
            dry_run=True,
            data={"action": "apply_patch", "path": str(path), "diff": "\n".join(before_after)},
        )

    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(original, encoding="utf-8")
    atomic_write_text(path, updated)
    return ToolResult(
        ok=True,
        data={
            "path": str(path),
            "backup": str(backup),
            "diff": "\n".join(before_after),
            "changed": original != updated,
        },
    )


def rollback_file(args: Dict[str, Any], **context: Any) -> ToolResult:
    workspace = context["workspace"]
    cfg: AgentConfig = context["config"]
    path = resolve_in_workspace(workspace, args.get("path"))
    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        return ToolResult(ok=False, error=f"No backup found for {path}")
    if cfg.dry_run:
        return ToolResult(ok=True, dry_run=True, data={"action": "rollback_file", "path": str(path)})
    atomic_write_text(path, backup.read_text(encoding="utf-8"))
    return ToolResult(ok=True, data={"path": str(path), "restored_from": str(backup)})


def build_patch_tools() -> List[ToolDefinition]:
    return [
        ToolDefinition(
            name="apply_patch",
            description="Apply a structured hunk patch or unified diff with uniqueness checks",
            argument_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "hunks": {"type": "array"},
                    "diff": {"type": "string"},
                },
                "required": ["path"],
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=apply_patch,
        ),
        ToolDefinition(
            name="rollback_file",
            description="Restore a file from its .bak backup",
            argument_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=False,
            handler=rollback_file,
        ),
    ]
