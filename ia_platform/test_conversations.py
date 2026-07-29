"""Tests for chat persistence."""

from __future__ import annotations

from pathlib import Path

from ia_platform.conversations import append_message, clear_messages, load_messages, save_messages


def test_load_empty_chat(tmp_path: Path) -> None:
    assert load_messages(tmp_path) == []


def test_append_and_load(tmp_path: Path) -> None:
    append_message(tmp_path, "user", "Olá")
    append_message(tmp_path, "agent", "Resposta")
    messages = load_messages(tmp_path)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["text"] == "Resposta"
    assert (tmp_path / ".agent" / "chat.json").is_file()


def test_clear_messages(tmp_path: Path) -> None:
    append_message(tmp_path, "user", "x")
    clear_messages(tmp_path)
    assert load_messages(tmp_path) == []


def test_trim_on_save(tmp_path: Path) -> None:
    from ia_platform import conversations as conv

    original_max = conv.MAX_MESSAGES
    conv.MAX_MESSAGES = 3
    try:
        msgs = [{"role": "user", "text": str(i), "ts": i} for i in range(5)]
        save_messages(tmp_path, msgs)
        loaded = load_messages(tmp_path)
        assert len(loaded) == 3
        assert loaded[0]["text"] == "2"
    finally:
        conv.MAX_MESSAGES = original_max
