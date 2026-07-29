"""Independent validation runner with baseline awareness."""

from __future__ import annotations

import shutil
import time
from typing import Dict, List, Optional, Set

from .config import AgentConfig
from .models import ValidationResult
from .project_index import ProjectIndex
from .tools.terminal import run_command


class Validator:
    def __init__(self, config: AgentConfig, project_index: ProjectIndex) -> None:
        self.config = config
        self.project_index = project_index
        self.baseline_failures: Set[str] = set()
        self.command_count = 0

    def discover_commands(self, preferred: Optional[List[str]] = None) -> List[str]:
        if preferred:
            return preferred
        commands: List[str] = []
        for key in ("test", "lint", "build"):
            commands.extend(self.project_index.detected_commands.get(key) or [])
        # Keep only executable first tokens that exist when possible.
        filtered = []
        for cmd in commands:
            token = cmd.split()[0]
            if token in {"python", "python3", "npm", "node", "pytest", "ruff", "mypy"} or shutil.which(token):
                filtered.append(cmd)
        # de-dup
        out: List[str] = []
        for cmd in filtered:
            if cmd not in out:
                out.append(cmd)
        return out[:6]

    def establish_baseline(self) -> List[ValidationResult]:
        results = self.run_all()
        self.baseline_failures = {r.command for r in results if not r.success}
        return results

    def run_all(self, preferred: Optional[List[str]] = None) -> List[ValidationResult]:
        results = []
        for command in self.discover_commands(preferred):
            results.append(self.run_one(command))
        return results

    def run_one(self, command: str) -> ValidationResult:
        if self.command_count >= self.config.max_commands:
            return ValidationResult(
                command=command,
                success=False,
                exit_code=124,
                stdout="",
                stderr="command budget exceeded",
                duration_seconds=0.0,
                category="environment",
            )
        self.command_count += 1
        started = time.time()
        # Skip clearly unavailable tools quickly.
        first = command.split()[0]
        if first in {"ruff", "mypy", "npm"} and shutil.which(first) is None:
            return ValidationResult(
                command=command,
                success=False,
                exit_code=127,
                stdout="",
                stderr=f"{first} not installed",
                duration_seconds=0.0,
                category="missing_tool",
            )
        result = run_command(
            {"command": command, "cwd": ".", "timeout": self.config.command_timeout},
            workspace=str(self.config.workspace),
            config=self.config,
        )
        duration = time.time() - started
        data = result.data
        success = result.ok
        category = "code"
        if data.get("timeout"):
            category = "timeout"
        elif data.get("exit_code") == 127 or "not found" in (result.error or "").lower():
            category = "missing_tool"
        elif command in self.baseline_failures and not success:
            category = "pre_existing"
        elif not success and command not in self.baseline_failures:
            category = "introduced"
        return ValidationResult(
            command=command,
            success=success,
            exit_code=int(data.get("exit_code", 1 if not success else 0)),
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "") or result.error or ""),
            duration_seconds=duration,
            category=category,
        )

    def summarize(self, results: List[ValidationResult]) -> str:
        if not results:
            return "No validations executed."
        lines = []
        for item in results:
            mark = "OK" if item.success else "FAIL"
            lines.append(
                f"[{mark}/{item.category}] {item.command} exit={item.exit_code} "
                f"stderr={item.stderr[:200]}"
            )
        return "\n".join(lines)
