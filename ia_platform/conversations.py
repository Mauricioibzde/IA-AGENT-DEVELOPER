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


def is_coding_scope_refusal(text: str) -> bool:
    """True when the model wrongly claims it can only discuss programming/tech."""
    t = str(text or "").strip().lower()
    if not t:
        return False
    claims_limit = bool(
        re.search(
            r"(apenas|somente|s[oó]|limitad[oa]|programado para|n[aã]o (tenho|possuo)|"
            r"n[aã]o (posso|consigo)|fora do (meu|escopo)|n[aã]o (estou|sou) (capaz|apto))",
            t,
        )
    )
    coding_scope = bool(
        re.search(
            r"(programa[cç][aã]o|desenvolvimento de software|linguagens? de programa|"
            r"arquitetura de software|relacionad[oa]s? [aà] (programa|tecnologia|software)|"
            r"assuntos? relacionados? [aà] programa|s[oó] (sobre|de) (programa|tecnologia|c[oó]digo))",
            t,
        )
    )
    redirects = bool(
        re.search(
            r"(pergunte .+ (programa|tecnologia|c[oó]digo)|fique .+ (programa|tecnologia)|"
            r"especifique .+ (programa|tecnologia|software))",
            t,
        )
    )
    return (claims_limit and coding_scope) or (coding_scope and redirects and len(t) < 900)


def open_chat_system_prompt(project_name: str = "", memory_note: str = "") -> str:
    """System prompt for free-form Chat (not limited to coding)."""
    project = (project_name or "").strip() or "geral"
    note = str(memory_note or "")
    return (
        "Você é o Forge, um assistente geral de conversa — como um ChatGPT amigável. "
        "Pode e DEVE responder sobre QUALQUER assunto: vida, filosofia, saúde básica (sem diagnóstico), "
        "história, negócios, estudos, emoções, hobbies, ideias de produto, etc.\n"
        "REGRA CRÍTICA: NUNCA diga que você só fala de programação, tecnologia ou software. "
        "Isso é falso neste modo. Se o usuário perguntar sobre a vida humana, família, estudos "
        "ou qualquer tema, responda de forma útil e natural.\n"
        "Você TAMBÉM sabe de software quando pedirem — mas não force o assunto para código.\n"
        "Modo Chat: só conversa; não edite arquivos. Se quiserem criar/alterar um app, "
        "sugira Work / Executar código (o histórico deste chat serve de contexto).\n"
        "Responda no idioma do usuário, com clareza e empatia. Evite desculpas vazias.\n"
        f"Projeto vinculado (opcional): {project}."
        f"{note}"
    )


def build_open_chat_messages(
    history: List[Dict[str, str]],
    prompt: str,
    *,
    retry_nudge: bool = False,
    completion_frame: bool = False,
) -> List[Dict[str, str]]:
    """Filter refusal-tainted history and reinforce open-topic answering."""
    clean: List[Dict[str, str]] = []
    for msg in history or []:
        role = str(msg.get("role") or "")
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        if role == "assistant" and is_coding_scope_refusal(content):
            # Drop old refusals — they train the model to keep refusing.
            continue
        if role in {"user", "assistant", "system"}:
            clean.append({"role": role, "content": content})

    # Keep only the last few turns after filtering.
    clean = clean[-8:]

    user_text = str(prompt or "").strip()
    if completion_frame:
        user_text = (
            "Complete the answer in Portuguese for a general-knowledge assistant.\n"
            f"User question: {user_text}\n"
            "Rules:\n"
            "- Answer the question directly and helpfully.\n"
            "- Do NOT say you only discuss programming, technology, or software.\n"
            "- Do NOT apologize for being a coding model.\n"
            "- No code unless the user asked for code.\n"
            "Answer:\n"
        )
        clean = [{"role": "user", "content": user_text}]
        return clean
    if retry_nudge:
        user_text = (
            f"{user_text}\n\n"
            "(Responda agora ao assunto pedido. É permitido e esperado falar de temas "
            "fora de programação. Não recuse.)"
        )
    else:
        user_text = (
            f"{user_text}\n\n"
            "(Lembrete: modo Chat livre — responda o tema pedido; não diga que só fala de código.)"
        )
    clean.append({"role": "user", "content": user_text})
    return clean


def looks_like_general_topic(prompt: str) -> bool:
    """Heuristic: user is asking something outside coding/tooling."""
    t = str(prompt or "").strip().lower()
    if not t:
        return False
    if re.search(
        r"\b(c[oó]digo|program|javascript|python|react|html|css|api|bug|deploy|git|"
        r"fun[cç][aã]o|classe|banco de dados|sql|docker|linux terminal)\b",
        t,
    ):
        return False
    return bool(
        re.search(
            r"\b(vida|amor|fam[ií]lia|felicidade|filosofia|hist[oó]ria|psicologia|"
            r"sa[uú]de|emo[cç][aã]o|sentimento|amizade|carreira(?! (dev|ti))|estudos?|"
            r"relig|espiritual|sentido|exist[eê]ncia|sociedade|pol[ií]tica|viagem|"
            r"comida|m[uú]sica|filme|livro|esporte|relacionamento)\b",
            t,
        )
    ) or (
        len(t) < 80
        and not re.search(r"\b(app|site|software|sistema|implement|fun[cç]|bug)\b", t)
    )


def general_chat_fallback_answer(prompt: str, *, model_name: str = "") -> str:
    """Last-resort reply when a coder model keeps refusing open topics."""
    t = str(prompt or "").strip().lower()
    model = (model_name or "modelo de código").strip()
    tip = (
        f"\n\n—\n"
        f"Obs.: o modelo local **{model}** é especializado em código e às vezes recusa "
        f"assuntos gerais. Para um Chat mais natural, baixe em **Modelos IA** algo como "
        f"`llama3.2:3b` ou `mistral:7b`. O Work continua ótimo para criar apps."
    )

    if re.search(r"vida humana|sentido da vida|sobre a vida|o que [eé] a vida", t):
        body = (
            "A vida humana é o tempo que temos para sentir, aprender, relacionar e escolher. "
            "Ela mistura necessidades concretas — saúde, segurança, trabalho — com buscas "
            "mais profundas de pertencimento, propósito e crescimento. "
            "Não existe um roteiro único: o valor costuma aparecer no cuidado com as pessoas, "
            "nas experiências que importam para você e na capacidade de recomeçar quando algo muda."
        )
    elif re.search(r"fam[ií]lia", t):
        body = (
            "Família pode ser laço de sangue ou as pessoas que escolhemos cuidar. "
            "Em geral funciona melhor com respeito, limites claros e comunicação honesta — "
            "nem sempre perfeita, mas com disposição de ouvir e reparar. "
            "Cada família tem sua cultura; o que importa é se as relações nutrem ou desgastam."
        )
    elif re.search(r"aprender a programar|como (eu )?posso aprender", t):
        body = (
            "Para aprender a programar: escolha uma linguagem (Python ou JavaScript são boas portas), "
            "pratique todo dia com exercícios pequenos e construa um projetinho real. "
            "Combine um curso estruturado com muita leitura de código e erros — errar faz parte. "
            "Quando quiser, no Forge use o Chat para tirar dúvidas e o Work para implementar."
        )
    else:
        body = (
            "Posso conversar sobre isso sim. Em poucas palavras: o tema que você trouxe faz parte "
            "da experiência humana — merece curiosidade, nuance e respeito ao contexto. "
            "Se quiser, me diga o que exatamente quer entender (um conceito, uma decisão, "
            "um sentimento ou um plano) que eu aprofundo no próximo passo."
        )
    return body + tip


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
