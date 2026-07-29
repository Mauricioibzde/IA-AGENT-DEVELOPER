"""Tests for conversation context formatting."""

from __future__ import annotations

from ia_platform.conversations import format_conversation_context


def test_format_conversation_context() -> None:
    messages = [
        {"role": "user", "text": "crie uma landing page"},
        {"role": "agent", "text": "Criei index.html"},
        {"role": "user", "text": "deixe azul"},
    ]
    ctx = format_conversation_context(messages)
    assert "Usuário: crie uma landing page" in ctx
    assert "Agente: Criei index.html" in ctx
    assert "deixe azul" in ctx


def test_format_empty() -> None:
    assert format_conversation_context([]) == ""
