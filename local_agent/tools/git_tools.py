"""Read-only Git inspection tools."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from ..models import RiskLevel, ToolDefinition, ToolResult


def _run_git(workspace: Path, args: List[str], timeout: int = 30) -> ToolResult:
    if not (workspace / ".git").exists():
        return ToolResult(ok=False, error="Not a git repository")
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, error="git command timed out")
    return ToolResult(
        ok=completed.returncode == 0,
        data={
            "command": "git " + " ".join(args),
            "exit_code": completed.returncode,
            "stdout": (completed.stdout or "").strip()[-8000:],
            "stderr": (completed.stderr or "").strip()[-4000:],
        },
        error=None if completed.returncode == 0 else (completed.stderr or "git failed").strip(),
    )


def git_status(args: Dict[str, Any], **context: Any) -> ToolResult:
    return _run_git(Path(context["workspace"]), ["status", "--short", "--branch"])


def git_diff(args: Dict[str, Any], **context: Any) -> ToolResult:
    extra = ["diff"]
    if args.get("staged"):
        extra.append("--staged")
    if args.get("path"):
        extra.extend(["--", str(args["path"])])
    return _run_git(Path(context["workspace"]), extra)


def git_log(args: Dict[str, Any], **context: Any) -> ToolResult:
    n = int(args.get("limit", 5))
    return _run_git(Path(context["workspace"]), ["log", f"-n{n}", "--oneline"])


def git_show(args: Dict[str, Any], **context: Any) -> ToolResult:
    ref = str(args.get("ref", "HEAD"))
    return _run_git(Path(context["workspace"]), ["show", "--stat", ref])


def git_branch(args: Dict[str, Any], **context: Any) -> ToolResult:
    return _run_git(Path(context["workspace"]), ["branch", "--show-current"])


def git_changed_files(args: Dict[str, Any], **context: Any) -> ToolResult:
    result = _run_git(Path(context["workspace"]), ["status", "--porcelain"])
    if not result.ok:
        return result
    files = []
    for line in result.data.get("stdout", "").splitlines():
        if len(line) >= 4:
            files.append(line[3:].strip())
    return ToolResult(ok=True, data={"files": files, "raw": result.data.get("stdout", "")})


def build_git_tools() -> List[ToolDefinition]:
    return [
        ToolDefinition("git_status", "Show git status", {"type": "object", "properties": {}}, RiskLevel.LOW, False, False, git_status),
        ToolDefinition("git_diff", "Show git diff", {"type": "object", "properties": {"staged": {"type": "boolean"}, "path": {"type": "string"}}}, RiskLevel.LOW, False, False, git_diff),
        ToolDefinition("git_log", "Show recent commits", {"type": "object", "properties": {"limit": {"type": "integer"}}}, RiskLevel.LOW, False, False, git_log),
        ToolDefinition("git_show", "Show a commit", {"type": "object", "properties": {"ref": {"type": "string"}}}, RiskLevel.LOW, False, False, git_show),
        ToolDefinition("git_branch", "Show current branch", {"type": "object", "properties": {}}, RiskLevel.LOW, False, False, git_branch),
        ToolDefinition("git_changed_files", "List changed files", {"type": "object", "properties": {}}, RiskLevel.LOW, False, False, git_changed_files),
    ]
