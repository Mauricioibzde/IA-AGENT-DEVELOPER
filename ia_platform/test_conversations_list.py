"""Conversation helpers tests."""

from __future__ import annotations

from pathlib import Path

from ia_platform.conversations import append_message, list_recent_chats


def test_list_recent_chats(tmp_path: Path) -> None:
    a = tmp_path / "alpha"
    b = tmp_path / "beta"
    a.mkdir()
    b.mkdir()
    append_message(a, "user", "Quero uma landing page moderna")
    append_message(a, "agent", "Claro")
    append_message(b, "user", "Explique o projeto")
    chats = list_recent_chats(tmp_path)
    assert len(chats) == 2
    assert chats[0]["project_id"] in {"alpha", "beta"}
    assert "landing" in chats[0]["title"].lower() or "explique" in chats[0]["title"].lower()
