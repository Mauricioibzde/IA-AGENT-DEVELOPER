"""Persist chat history per project under .agent/chat.json."""

from __future__ import annotations

import json
import re
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


def list_recent_chats(projects_root: Path, *, limit: int = 40) -> List[Dict[str, Any]]:
    """Summaries of project conversations for the sidebar Chats section."""
    projects_root.mkdir(parents=True, exist_ok=True)
    chats: List[Dict[str, Any]] = []
    for entry in projects_root.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        messages = load_messages(entry)
        if not messages:
            continue
        first_user = next((m for m in messages if m.get("role") == "user" and str(m.get("text") or "").strip()), None)
        last = messages[-1]
        title_src = str((first_user or last).get("text") or entry.name).strip().replace("\n", " ")
        title = title_src[:64] + ("…" if len(title_src) > 64 else "")
        chats.append(
            {
                "project_id": entry.name,
                "project_name": entry.name,
                "title": title or entry.name,
                "updated": float(last.get("ts") or entry.stat().st_mtime),
                "message_count": len(messages),
                "last_role": last.get("role"),
            }
        )
    chats.sort(key=lambda item: item.get("updated") or 0, reverse=True)
    return chats[:limit]


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
            lines.append(f"{prefix}{text[:1600]}")
        else:
            lines.append(f"Sistema: {text[:400]}")
    return "\n".join(lines)


def looks_like_implement_follow_up(goal: str) -> bool:
    text = str(goal or "").strip().lower()
    if not text:
        return False
    if re.search(
        r"\b(implement(e|ar)?|aplique|aplica|realize|execute|adicione|fa[cç]a|coloque)\b",
        text,
    ) and re.search(
        r"\b(isso|ess[ea]s?|aquilo|melhorias?|sugest\w*|altera[cç]\w*|mudan[cç]\w*|pedido|no projeto|no c[oó]digo|no chat)\b",
        text,
    ):
        return True
    if re.match(r"^implemente(\s+(vc|voc[eê]|as|isso|essas?))?", text):
        return True
    if re.match(r"^(aplica|aplique|fa[cç]a)\s+(as\s+)?(melhorias|sugest|mudan|altera)", text):
        return True
    return False


def enrich_goal_with_conversation(goal: str, conversation: str) -> str:
    """Stitch recent chat into Work goals so exploration → implementation stays connected."""
    goal_text = str(goal or "").strip()
    conv = str(conversation or "").strip()
    if not goal_text or not conv:
        return goal_text
    if "--- contexto" in goal_text.lower() or "aplique isto" in goal_text.lower():
        return goal_text

    # Strong follow-ups: force applying prior suggestions.
    if looks_like_implement_follow_up(goal_text):
        return (
            f"{goal_text}\n\n"
            "--- Contexto do chat anterior (APLIQUE no código do projeto) ---\n"
            f"{conv[:4500]}\n"
            "--- Fim do contexto ---\n"
            "Edite os arquivos necessários agora; não responda só com texto."
        )

    # Soft link: short/ambiguous work goals still benefit from prior discussion
    # (business context, audience, flows) without overriding an already-detailed prompt.
    if len(goal_text) <= 220 or re.search(
        r"\b(discutimos|combinamos|falamos|combinado|como combinado|do chat|da conversa|"
        r"o que (a gente|nós) (falou|definiu|planejou)|com base nisso|nesse contexto)\b",
        goal_text.lower(),
    ):
        return (
            f"{goal_text}\n\n"
            "--- Contexto recente do Chat (use para entender a situação antes de codar) ---\n"
            f"{conv[:3500]}\n"
            "--- Fim do contexto ---"
        )
    return goal_text
