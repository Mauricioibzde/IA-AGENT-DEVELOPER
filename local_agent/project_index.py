"""Project indexing and structural summary (no embeddings)."""

from __future__ import annotations

import json
import re
import shutil
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
    ".scss": "css",
    ".html": "html",
    ".sh": "shell",
    ".ps1": "powershell",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".sql": "sql",
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

    def build(self, max_files: int = 400, *, use_cache: bool = True) -> "ProjectIndex":
        cache_path = self.workspace / ".agent" / "index.json"
        if use_cache and self._load_cache(cache_path, max_files):
            return self

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
        if use_cache:
            self._save_cache(cache_path, max_files)
        return self

    def _fingerprint(self) -> str:
        """Cheap fingerprint: count + newest mtime of tracked tree roots."""
        newest = 0.0
        count = 0
        for path in self._iter_files():
            try:
                newest = max(newest, path.stat().st_mtime)
            except OSError:
                continue
            count += 1
            if count >= 500:
                break
        return f"{count}:{int(newest)}"

    def _load_cache(self, cache_path: Path, max_files: int) -> bool:
        if not cache_path.is_file():
            return False
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        if not isinstance(data, dict) or data.get("fingerprint") != self._fingerprint():
            return False
        if int(data.get("max_files") or 0) != max_files:
            return False
        files_raw = data.get("files")
        if not isinstance(files_raw, list):
            return False
        self.files = [
            ProjectFile(
                path=str(item.get("path", "")),
                language=item.get("language"),
                size=int(item.get("size") or 0),
                imports=list(item.get("imports") or [])[:40],
                symbols=list(item.get("symbols") or [])[:80],
                is_config=bool(item.get("is_config")),
                is_test=bool(item.get("is_test")),
            )
            for item in files_raw
            if isinstance(item, dict) and item.get("path")
        ]
        self.package_scripts = dict(data.get("package_scripts") or {})
        detected = data.get("detected_commands") or {}
        if isinstance(detected, dict):
            self.detected_commands = {
                "test": list(detected.get("test") or []),
                "build": list(detected.get("build") or []),
                "lint": list(detected.get("lint") or []),
                "format": list(detected.get("format") or []),
            }
        return True

    def _save_cache(self, cache_path: Path, max_files: int) -> None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "fingerprint": self._fingerprint(),
                "max_files": max_files,
                "package_scripts": self.package_scripts,
                "detected_commands": self.detected_commands,
                "files": [
                    {
                        "path": f.path,
                        "language": f.language,
                        "size": f.size,
                        "imports": f.imports[:20],
                        "symbols": f.symbols[:40],
                        "is_config": f.is_config,
                        "is_test": f.is_test,
                    }
                    for f in self.files
                ],
            }
            cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

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

    def search_relevant(self, query: str, limit: int = 8) -> List[ProjectFile]:
        """Keyword search over paths, symbols, and imports (RAG-lite, no embeddings)."""
        tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) >= 3]
        if not tokens:
            return []

        scored: List[tuple[int, ProjectFile]] = []
        for item in self.files:
            score = 0
            path_lower = item.path.lower()
            name_lower = path_lower.rsplit("/", 1)[-1]
            for token in tokens:
                if token in name_lower:
                    score += 4
                elif token in path_lower:
                    score += 3
                if any(token in sym.lower() for sym in item.symbols[:12]):
                    score += 2
                if any(token in imp.lower() for imp in item.imports[:12]):
                    score += 1
                if item.is_config and token in path_lower:
                    score += 2
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].path))
        seen: set[str] = set()
        results: List[ProjectFile] = []
        for _, item in scored:
            if item.path in seen:
                continue
            seen.add(item.path)
            results.append(item)
            if len(results) >= limit:
                break
        return results

    def relevant_summary(self, query: str, limit: int = 8) -> str:
        matches = self.search_relevant(query, limit=limit)
        if not matches:
            return ""
        lines = ["Arquivos relevantes para o objetivo:"]
        for item in matches:
            syms = ", ".join(item.symbols[:4])
            extra = f" — símbolos: {syms}" if syms else ""
            lines.append(f"- {item.path} [{item.language or '?'}]{extra}")
        return "\n".join(lines)

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
            py = "python3" if shutil.which("python3") else "python"
            self.detected_commands["test"].append(f"{py} -m pytest -q")
            self.detected_commands["lint"].extend([f"{py} -m compileall .", "ruff check ."])
            self.detected_commands["build"].append(f"{py} -m compileall .")

        if (self.workspace / "go.mod").exists() or any(f.language == "go" for f in self.files):
            self.detected_commands["test"].append("go test ./...")
            self.detected_commands["build"].append("go build ./...")
            self.detected_commands["lint"].append("go vet ./...")

        if (self.workspace / "Cargo.toml").exists() or any(f.language == "rust" for f in self.files):
            self.detected_commands["test"].append("cargo test")
            self.detected_commands["build"].append("cargo check")
            self.detected_commands["lint"].append("cargo clippy -- -D warnings")

        if (self.workspace / "pom.xml").exists():
            self.detected_commands["test"].append("mvn -q test")
            self.detected_commands["build"].append("mvn -q -DskipTests package")
        elif (self.workspace / "build.gradle").exists() or (self.workspace / "build.gradle.kts").exists():
            self.detected_commands["test"].append("gradle test")
            self.detected_commands["build"].append("gradle build -x test")

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
