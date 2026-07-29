"""Sandboxed terminal execution with risk classification."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from typing import Any, Dict, List, Pattern, Tuple

from ..config import AgentConfig
from ..models import RiskLevel, ToolDefinition, ToolResult
from ..security import resolve_in_workspace

SHELL_REQUIRED_CHARS = set("&|;<>*(){}[]$`\\")

BLOCKED_PATTERNS: List[Pattern[str]] = [
    re.compile(r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?(/|~|\.\.)", re.I),
    re.compile(r"\brm\s+-rf\s+/", re.I),
    re.compile(r"\bdel\s+/s\b", re.I),
    re.compile(r"\bformat\b", re.I),
    re.compile(r"\b(shutdown|reboot|poweroff)\b", re.I),
    re.compile(r"\bsudo\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f", re.I),
    re.compile(r"\bgit\s+push\s+[^\n]*--force\b", re.I),
    re.compile(r"\bgit\s+push\s+[^\n]*-f\b", re.I),
    re.compile(r"(curl|wget).*\|\s*(sh|bash|zsh|powershell)", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\s+if=", re.I),
    re.compile(r">\s*/dev/sd", re.I),
    re.compile(r"\bchmod\s+-R\s+777\b", re.I),
    re.compile(r"\bchown\s+-R\b", re.I),
]

HIGH_RISK_HINTS = [
    re.compile(r"\brm\b", re.I),
    re.compile(r"\bgit\s+push\b", re.I),
    re.compile(r"\bcurl\b|\bwget\b", re.I),
    re.compile(r"\bchmod\b|\bchown\b", re.I),
]

MEDIUM_RISK_HINTS = [
    re.compile(r"\bpip\s+install\b|\bnpm\s+install\b|\byarn\s+add\b", re.I),
    re.compile(r"\bblack\b|\bruff\s+format\b|\bprettier\b", re.I),
]

LOW_RISK_HINTS = [
    re.compile(r"\bpytest\b|\bnpm\s+test\b|\bnpm\s+run\s+(test|lint|build|typecheck)\b", re.I),
    re.compile(r"\bgit\s+(status|diff|log|show|branch)\b", re.I),
    re.compile(r"\bls\b|\bdir\b|\bcat\b|\btype\b|\bpython\s+-m\s+compileall\b", re.I),
]


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*([^\s'\"]+)"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
]


def classify_command_risk(command: str) -> RiskLevel:
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            return RiskLevel.CRITICAL
    for pattern in HIGH_RISK_HINTS:
        if pattern.search(command):
            return RiskLevel.HIGH
    for pattern in MEDIUM_RISK_HINTS:
        if pattern.search(command):
            return RiskLevel.MEDIUM
    for pattern in LOW_RISK_HINTS:
        if pattern.search(command):
            return RiskLevel.LOW
    return RiskLevel.MEDIUM


def is_command_blocked(command: str) -> Tuple[bool, str]:
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            return True, f"Blocked dangerous command pattern: {pattern.pattern}"
    # Block path escapes via cd outside and absolute destructive ops.
    if re.search(r"\bcd\s+/(?!tmp\b)", command):
        return True, "Blocked cd outside workspace-like absolute roots"
    return False, ""


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda m: m.group(0)[: m.start(0) and 0 :] + "[REDACTED]", redacted)
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _maybe_shell(command: str) -> tuple[Any, bool]:
    if any(ch in command for ch in SHELL_REQUIRED_CHARS) or "&&" in command or "||" in command:
        return command, True
    try:
        return shlex.split(command, posix=os.name != "nt"), False
    except ValueError:
        return command, True


def run_command(args: Dict[str, Any], **context: Any) -> ToolResult:
    cfg: AgentConfig = context["config"]
    workspace = context["workspace"]
    command = str(args.get("command", "")).strip()
    if not command:
        return ToolResult(ok=False, error="run_command requires a non-empty command")

    blocked, reason = is_command_blocked(command)
    if blocked:
        return ToolResult(ok=False, error=reason, data={"command": command, "blocked": True})

    risk = classify_command_risk(command)
    if risk == RiskLevel.CRITICAL:
        return ToolResult(
            ok=False,
            error=f"Comando crítico bloqueado: {command}",
            data={"command": command, "risk_level": risk.value, "confirmation_required": True},
        )
    if risk == RiskLevel.HIGH:
        # Never auto-approve HIGH (rm, curl, chmod, git push, …).
        return ToolResult(
            ok=False,
            error=(
                f"Ação sensível bloqueada: revise antes de continuar "
                f"(comando com risco={risk.value})."
            ),
            data={"command": command, "risk_level": risk.value, "confirmation_required": True},
        )
    if risk == RiskLevel.MEDIUM and not cfg.auto_approve_low_risk:
        return ToolResult(
            ok=False,
            error=(
                f"Ação sensível bloqueada: revise antes de continuar "
                f"(comando com risco={risk.value})."
            ),
            data={"command": command, "risk_level": risk.value, "confirmation_required": True},
        )

    cwd = resolve_in_workspace(workspace, args.get("cwd", "."))
    timeout = int(args.get("timeout", cfg.command_timeout))
    if cfg.dry_run:
        return ToolResult(
            ok=True,
            dry_run=True,
            data={"action": "run_command", "command": command, "cwd": str(cwd), "risk_level": risk.value},
        )

    argv, use_shell = _maybe_shell(command)
    try:
        completed = subprocess.run(
            argv,
            shell=use_shell,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return ToolResult(
            ok=False,
            error=f"Command timed out after {timeout}s",
            data={
                "command": command,
                "cwd": str(cwd),
                "timeout": True,
                "stdout": redact_secrets((exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else ""),
                "stderr": redact_secrets((exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else ""),
            },
        )

    stdout = redact_secrets((completed.stdout or "")[-8000:])
    stderr = redact_secrets((completed.stderr or "")[-8000:])
    return ToolResult(
        ok=completed.returncode == 0,
        data={
            "command": command,
            "cwd": str(cwd),
            "exit_code": completed.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "shell": use_shell,
            "risk_level": risk.value,
        },
        error=None if completed.returncode == 0 else f"Command failed with exit code {completed.returncode}",
    )


def build_terminal_tools() -> List[ToolDefinition]:
    return [
        ToolDefinition(
            name="run_command",
            description="Run a shell/argv command inside the workspace with risk checks",
            argument_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["command"],
            },
            risk_level=RiskLevel.MEDIUM,
            mutating=True,
            requires_confirmation=True,
            handler=run_command,
        )
    ]
