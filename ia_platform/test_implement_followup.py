"""Tests for implement-follow-up goal enrichment."""

from __future__ import annotations

from ia_platform.conversations import enrich_goal_with_conversation, looks_like_implement_follow_up


def test_detects_short_implement_imperatives() -> None:
    assert looks_like_implement_follow_up("IMPLEMENTE VC AS MELHORIAS")
    assert looks_like_implement_follow_up("implemente as sugestões")
    assert looks_like_implement_follow_up("aplique as mudanças no projeto")
    assert not looks_like_implement_follow_up("oi")
    assert not looks_like_implement_follow_up("me explica o que é CSS")


def test_enrich_goal_appends_chat_context() -> None:
    goal = "IMPLEMENTE VC AS MELHORIAS"
    conversation = "Agente: Use position:fixed na sidebar e ajuste o main."
    enriched = enrich_goal_with_conversation(goal, conversation)
    assert "position:fixed" in enriched
    assert "APLIQUE" in enriched
    # Idempotent when already enriched by the frontend.
    again = enrich_goal_with_conversation(enriched, conversation)
    assert again == enriched


def test_enrich_short_work_goal_keeps_chat_situation_context() -> None:
    goal = "Crie a primeira versão do app"
    conversation = "Usuário: Quero um app para organizar pedidos de uma padaria local."
    enriched = enrich_goal_with_conversation(goal, conversation)
    assert "padaria" in enriched
    assert "Contexto recente do Chat" in enriched
