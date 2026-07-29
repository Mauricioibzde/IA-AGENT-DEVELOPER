"""Project indexing and structural summary (no embeddings)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import ProjectFile
from .security import is_probably_binary

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

LANG_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".css": "css",
    ".html": "html",
    ".sh": "shell",
    ".ps1": "powershell",
}

CONFIG_NAMES = {
    "pyproject.toml",
    "package.json",
    "tsconfig.json",
    "setup.cfg",
    "setup.py",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    ".env.example",
    "vite.config.ts",
    "vite.config.js",
}


class ProjectIndex:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.files: List[ProjectFile] = []
        self.package_scripts: Dict[str, str] = {}
        self.detected_commands: Dict[str, List[str]] = {
            "test": [],
            "build": [],
            "lint": [],
            "format": [],
        }

    def build(self, max_files: int = 400) -> "ProjectIndex":
        self.files = []
        count = 0
        for path in self._iter_files():
            rel = str(path.relative_to(self.workspace)).replace("\\", "/")
            language = LANG_BY_EXT.get(path.suffix.lower())
            size = path.stat().st_size
            imports: List[str] = []
            symbols: List[str] = []
            if language == "python" and size < 200_000 and not is_probably_binary(path):
                text = self._safe_read(path)
                imports = re.findall(r"^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)", text, re.M)
                symbols = re.findall(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M)
            elif language in {"javascript", "typescript"} and size < 200_000 and not is_probably_binary(path):
                text = self._safe_read(path)
                imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", text)
                symbols = re.findall(
                    r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)|"
                    r"^\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)",
                    text,
                    re.M,
                )
                symbols = [s for pair in symbols for s in pair if s]
            self.files.append(
                ProjectFile(
                    path=rel,
                    language=language,
                    size=size,
                    imports=imports[:40],
                    symbols=symbols[:80],
                    is_config=path.name in CONFIG_NAMES,
                    is_test=("test" in rel.lower() or path.name.startswith("test_")),
                )
            )
            count += 1
            if count >= max_files:
                break
        self._detect_commands()
        return self

    def summary(self, limit: int = 40) -> str:
        lines = [f"Workspace: {self.workspace}", f"Indexed files: {len(self.files)}"]
        configs = [f.path for f in self.files if f.is_config][:15]
        if configs:
            lines.append("Config files: " + ", ".join(configs))
        if self.package_scripts:
            lines.append("package.json scripts: " + ", ".join(sorted(self.package_scripts)))
        for key, cmds in self.detected_commands.items():
            if cmds:
                lines.append(f"{key} commands: " + ", ".join(cmds))
        lines.append("Sample files:")
        for item in self.files[:limit]:
            lang = item.language or "unknown"
            lines.append(f"- {item.path} [{lang}] ({item.size} bytes)")
        return "\n".join(lines)

    def find_by_name(self, query: str) -> List[ProjectFile]:
        q = query.lower()
        return [f for f in self.files if q in f.path.lower()]

    def find_by_symbol(self, symbol: str) -> List[ProjectFile]:
        return [f for f in self.files if symbol in f.symbols]

    def _detect_commands(self) -> None:
        pkg = self.workspace / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                scripts = data.get("scripts") or {}
                if isinstance(scripts, dict):
                    self.package_scripts = {str(k): str(v) for k, v in scripts.items()}
                    for name in scripts:
                        cmd = f"npm run {name}"
                        lname = name.lower()
                        if "test" in lname:
                            self.detected_commands["test"].append(cmd)
                        if lname in {"build", "compile"}:
                            self.detected_commands["build"].append(cmd)
                        if "lint" in lname or "typecheck" in lname:
                            self.detected_commands["lint"].append(cmd)
                        if "format" in lname:
                            self.detected_commands["format"].append(cmd)
            except Exception:
                pass

        if (self.workspace / "pyproject.toml").exists() or any(f.language == "python" for f in self.files):
            self.detected_commands["test"].append("python -m pytest -q")
            self.detected_commands["lint"].extend(["python -m compileall .", "ruff check ."])
            self.detected_commands["build"].append("python -m compileall .")

        # de-dup
        for key, values in self.detected_commands.items():
            seen = []
            for item in values:
                if item not in seen:
                    seen.append(item)
            self.detected_commands[key] = seen

    def _iter_files(self) -> Iterable[Path]:
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORE_DIRS for part in path.parts):
                continue
            yield path

    @staticmethod
    def _safe_read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""
