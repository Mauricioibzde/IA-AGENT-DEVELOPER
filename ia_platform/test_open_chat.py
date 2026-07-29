"""Open-ended Chat helpers (not limited to programming)."""

from __future__ import annotations

from ia_platform.conversations import (
    build_open_chat_messages,
    is_coding_scope_refusal,
    open_chat_system_prompt,
)


def test_detects_coding_scope_refusal() -> None:
    refusal = (
        "Desculpe, mas como assistente de IA, estou programado para responder perguntas "
        "relacionadas à programação e tecnologia. Não tenho o conhecimento necessário "
        "para discutir a vida humana."
    )
    assert is_coding_scope_refusal(refusal)
    assert not is_coding_scope_refusal(
        "A vida humana envolve relações, trabalho, aprendizado e busca de sentido."
    )


def test_build_open_chat_drops_refusal_history() -> None:
    history = [
        {"role": "user", "content": "oi"},
        {
            "role": "assistant",
            "content": "Só posso ajudar com programação e desenvolvimento de software.",
        },
        {"role": "user", "content": "como está o tempo?"},
    ]
    messages = build_open_chat_messages(history, "me fale sobre a vida humana")
    assert all(not is_coding_scope_refusal(m["content"]) for m in messages if m["role"] == "assistant")
    assert messages[-1]["role"] == "user"
    assert "vida humana" in messages[-1]["content"]
    assert "Chat livre" in messages[-1]["content"]


def test_open_chat_system_prompt_forbids_coding_only_claim() -> None:
    prompt = open_chat_system_prompt("demo")
    assert "NUNCA diga" in prompt
    assert "QUALQUER assunto" in prompt or "qualquer assunto" in prompt.lower()


def test_general_chat_fallback_answers_life_topic() -> None:
    from ia_platform.conversations import general_chat_fallback_answer

    text = general_chat_fallback_answer(
        "me explique um pouco sobre a vida humana",
        model_name="deepseek-coder:6.7b",
    )
    assert "vida humana" in text.lower() or "experiências" in text.lower() or "aprender" in text.lower()
    assert "llama3.2" in text.lower()
    assert not is_coding_scope_refusal(text.split("—")[0])
