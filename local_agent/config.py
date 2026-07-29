"""Configuration for the local coding agent."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _normalize_host(host: str) -> str:
    value = host.strip() or "http://127.0.0.1:11434"
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    return value.rstrip("/")


@dataclass
class AgentConfig:
    workspace: Path
    model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    planner_model: str = field(default_factory=lambda: _env("OLLAMA_PLANNER_MODEL", "") or _env("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    coder_model: str = field(default_factory=lambda: _env("OLLAMA_CODER_MODEL", "") or _env("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    reflection_model: str = field(default_factory=lambda: _env("OLLAMA_REFLECTION_MODEL", "") or _env("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    ollama_host: str = field(default_factory=lambda: _normalize_host(_env("OLLAMA_HOST", "http://127.0.0.1:11434")))
    max_steps: int = field(default_factory=lambda: _env_int("AGENT_MAX_STEPS", 12))
    max_task_attempts: int = field(default_factory=lambda: _env_int("AGENT_MAX_TASK_ATTEMPTS", 3))
    max_model_calls: int = field(default_factory=lambda: _env_int("AGENT_MAX_MODEL_CALLS", 40))
    max_commands: int = field(default_factory=lambda: _env_int("AGENT_MAX_COMMANDS", 30))
    max_modified_files: int = field(default_factory=lambda: _env_int("AGENT_MAX_MODIFIED_FILES", 40))
    max_context_chars: int = field(default_factory=lambda: _env_int("AGENT_MAX_CONTEXT_CHARS", 24000))
    command_timeout: int = field(default_factory=lambda: _env_int("AGENT_COMMAND_TIMEOUT", 60))
    read_file_max_bytes: int = field(default_factory=lambda: _env_int("AGENT_READ_FILE_MAX_BYTES", 200_000))
    dry_run: bool = False
    verbose: bool = False
    debug: bool = False
    plan_only: bool = False
    use_memory: bool = True
    use_git: bool = True
    auto_approve_low_risk: bool = True
    log_level: str = "normal"

    @classmethod
    def from_args(
        cls,
        workspace: str | Path,
        *,
        model: Optional[str] = None,
        planner_model: Optional[str] = None,
        reflection_model: Optional[str] = None,
        max_steps: Optional[int] = None,
        max_task_attempts: Optional[int] = None,
        command_timeout: Optional[int] = None,
        dry_run: bool = False,
        verbose: bool = False,
        debug: bool = False,
        plan_only: bool = False,
        no_memory: bool = False,
        no_git: bool = False,
        auto_approve_low_risk: bool = True,
        config_path: Optional[str] = None,
    ) -> "AgentConfig":
        data: Dict[str, Any] = {}
        if config_path:
            path = Path(config_path)
            if path.exists():
                text = path.read_text(encoding="utf-8")
                if path.suffix.lower() in {".json"}:
                    data = json.loads(text)
                else:
                    # Minimal KEY=VALUE parser for .env-style files.
                    for line in text.splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, value = line.split("=", 1)
                        data[key.strip()] = value.strip().strip('"').strip("'")

        cfg = cls(workspace=Path(workspace).resolve())
        if model or data.get("OLLAMA_MODEL") or data.get("model"):
            cfg.model = str(model or data.get("OLLAMA_MODEL") or data.get("model"))
            cfg.coder_model = cfg.model
        if planner_model or data.get("OLLAMA_PLANNER_MODEL") or data.get("planner_model"):
            cfg.planner_model = str(planner_model or data.get("OLLAMA_PLANNER_MODEL") or data.get("planner_model"))
        else:
            cfg.planner_model = cfg.model
        if reflection_model or data.get("OLLAMA_REFLECTION_MODEL") or data.get("reflection_model"):
            cfg.reflection_model = str(
                reflection_model or data.get("OLLAMA_REFLECTION_MODEL") or data.get("reflection_model")
            )
        else:
            cfg.reflection_model = cfg.model
        if data.get("OLLAMA_HOST"):
            cfg.ollama_host = _normalize_host(str(data["OLLAMA_HOST"]))
        if max_steps is not None:
            cfg.max_steps = max_steps
        if max_task_attempts is not None:
            cfg.max_task_attempts = max_task_attempts
        if command_timeout is not None:
            cfg.command_timeout = command_timeout
        cfg.dry_run = dry_run
        cfg.verbose = verbose
        cfg.debug = debug
        cfg.plan_only = plan_only
        cfg.use_memory = not no_memory
        cfg.use_git = not no_git
        cfg.auto_approve_low_risk = auto_approve_low_risk
        if debug:
            cfg.log_level = "debug"
        elif verbose:
            cfg.log_level = "verbose"
        return cfg
