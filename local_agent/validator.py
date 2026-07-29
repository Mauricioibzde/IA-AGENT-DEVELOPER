"""Independent validation runner with baseline awareness."""

from __future__ import annotations

import re
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
        # run_all() categorizes before baseline_failures is known — re-tag so
        # pre-existing failures are not treated as agent-introduced regressions.
        for item in results:
            if not item.success and item.command in self.baseline_failures:
                item.category = "pre_existing"
        return results

    def run_all(self, preferred: Optional[List[str]] = None) -> List[ValidationResult]:
        results = []
        for command in self.discover_commands(preferred):
            results.append(self.run_one(command))
        return results

    def ensure_node_dependencies(self) -> Optional[ValidationResult]:
        """Run npm install once when package.json exists without node_modules."""
        pkg = self.config.workspace / "package.json"
        modules = self.config.workspace / "node_modules"
        if not pkg.is_file() or modules.is_dir():
            return None
        if shutil.which("npm") is None:
            return ValidationResult(
                command="npm install",
                success=False,
                exit_code=127,
                stdout="",
                stderr="npm not installed",
                duration_seconds=0.0,
                category="missing_tool",
            )
        # Allow a longer install budget without permanently raising command_timeout.
        previous = self.config.command_timeout
        try:
            self.config.command_timeout = max(previous, 180)
            return self.run_one("npm install")
        finally:
            self.config.command_timeout = previous

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

    @staticmethod
    def _tail(text: str, lines: int = 40) -> str:
        parts = (text or "").splitlines()
        if len(parts) <= lines:
            return "\n".join(parts)
        return "\n".join(parts[-lines:])

    @staticmethod
    def _extract_diagnostics(text: str) -> List[str]:
        hits: List[str] = []
        for line in (text or "").splitlines():
            if re.search(r"error|ERROR|FAIL|failed|Cannot find|Module not found|TS\d+|SyntaxError", line):
                hits.append(line.strip()[:240])
            elif re.search(r"[\w./\\-]+\.(py|js|jsx|ts|tsx|css|html):\d+", line):
                hits.append(line.strip()[:240])
            if len(hits) >= 8:
                break
        return hits

    def summarize(self, results: List[ValidationResult]) -> str:
        if not results:
            return "No validations executed."
        lines = []
        for item in results:
            mark = "OK" if item.success else "FAIL"
            combined = "\n".join(filter(None, [item.stdout, item.stderr]))
            diag = self._extract_diagnostics(combined)
            tail = self._tail(combined, 30)
            detail = "; ".join(diag) if diag else tail[:500]
            lines.append(
                f"[{mark}/{item.category}] {item.command} exit={item.exit_code}\n"
                f"  diagnostic: {detail[:700] or '(empty output)'}"
            )
        return "\n".join(lines)
