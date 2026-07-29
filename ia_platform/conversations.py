"""Persist chat history per project under .agent/chat.json."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

CHAT_FILENAME = "chat.json"
MAX_MESSAGES = 500


def _chat_file(project_dir: Path) -> Path:
    return project_dir / ".agent" / CHAT_FILENAME


def load_messages(project_dir: Path) -> List[Dict[str, Any]]:
    path = _chat_file(project_dir)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    messages = data.get("messages") if isinstance(data, dict) else None
    return list(messages) if isinstance(messages, list) else []


def save_messages(project_dir: Path, messages: List[Dict[str, Any]]) -> None:
    agent_dir = project_dir / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    trimmed = messages[-MAX_MESSAGES:]
    payload = {"messages": trimmed, "updated": time.time()}
    _chat_file(project_dir).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_message(
    project_dir: Path,
    role: str,
    text: str,
    meta: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    messages = load_messages(project_dir)
    entry: Dict[str, Any] = {"role": role, "text": text, "ts": time.time()}
    if meta:
        entry["meta"] = meta
    messages.append(entry)
    save_messages(project_dir, messages)
    return messages


def append_messages(project_dir: Path, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    messages = load_messages(project_dir)
    now = time.time()
    for item in entries:
        role = str(item.get("role", "system"))
        text = str(item.get("text", ""))
        entry: Dict[str, Any] = {"role": role, "text": text, "ts": item.get("ts") or now}
        meta = item.get("meta")
        if isinstance(meta, dict):
            entry["meta"] = meta
        messages.append(entry)
    save_messages(project_dir, messages)
    return messages


def clear_messages(project_dir: Path) -> None:
    save_messages(project_dir, [])


def format_conversation_context(messages: List[Dict[str, Any]], limit: int = 16) -> str:
    """Format prior chat turns for injection into the agent context."""
    if not messages:
        return ""
    trimmed = messages[-limit:]
    lines: List[str] = []
    for msg in trimmed:
        role = str(msg.get("role", "system"))
        text = str(msg.get("text", "")).strip()
        if not text:
            continue
        if role == "user":
            lines.append(f"Usuário: {text[:1200]}")
        elif role == "agent":
            meta = msg.get("meta") if isinstance(msg.get("meta"), dict) else {}
            status = meta.get("status")
            prefix = f"Agente ({status}): " if status else "Agente: "
            lines.append(f"{prefix}{text[:800]}")
        else:
            lines.append(f"Sistema: {text[:400]}")
    return "\n".join(lines)
