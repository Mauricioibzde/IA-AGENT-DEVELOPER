"""Structured logging helpers."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import AgentConfig


class AgentLogger:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def _emit(self, level: str, event: str, **fields: Any) -> None:
        rank = {"quiet": 0, "normal": 1, "verbose": 2, "debug": 3}
        current = rank.get(self.config.log_level, 1)
        needed = {"ERROR": 0, "WARN": 1, "INFO": 1, "DEBUG": 3}.get(level, 1)
        if event.startswith("tool_") or event.startswith("llm_"):
            needed = 2 if level != "ERROR" else 0
        if event in {"agent_step", "plan_created", "reflection", "validation"} and level == "INFO":
            needed = 1
        if current < needed and level not in {"ERROR", "WARN"}:
            if not (self.config.verbose and needed <= 2):
                if not (self.config.debug and needed <= 3):
                    if level == "INFO" and needed > current:
                        return

        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
        }
        for key, value in fields.items():
            if key.lower() in {"token", "password", "api_key", "secret"}:
                continue
            payload[key] = value

        stream = sys.stderr if level in {"ERROR", "WARN", "DEBUG"} or self.config.debug else sys.stdout
        if self.config.debug or self.config.log_level == "debug":
            print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        else:
            message = payload.get("message") or event
            extras = {k: v for k, v in payload.items() if k not in {"timestamp", "level", "event", "message"}}
            if extras and (self.config.verbose or level in {"ERROR", "WARN"}):
                print(f"[{level}] {message} {extras}", file=stream)
            else:
                print(f"[{level}] {message}", file=stream)

    def info(self, event: str, message: Optional[str] = None, **fields: Any) -> None:
        self._emit("INFO", event, message=message or event, **fields)

    def warn(self, event: str, message: Optional[str] = None, **fields: Any) -> None:
        self._emit("WARN", event, message=message or event, **fields)

    def error(self, event: str, message: Optional[str] = None, **fields: Any) -> None:
        self._emit("ERROR", event, message=message or event, **fields)

    def debug(self, event: str, message: Optional[str] = None, **fields: Any) -> None:
        self._emit("DEBUG", event, message=message or event, **fields)
