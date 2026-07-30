"""Unit tests for Ollama vision mockup description."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from ia_platform.visual_engine.vision import (
    describe_mockup,
    is_vision_model_name,
    pick_vision_model,
)


def test_is_vision_model_name() -> None:
    assert is_vision_model_name("llava:7b")
    assert is_vision_model_name("qwen2.5-vl:7b")
    assert is_vision_model_name("llama3.2-vision")
    assert not is_vision_model_name("qwen2.5-coder:7b")
    assert not is_vision_model_name("")


def test_pick_vision_model_prefers_llava() -> None:
    installed = ["qwen2.5-coder:7b", "llava:7b", "moondream"]
    assert pick_vision_model(installed) == "llava:7b"


def test_pick_vision_model_honors_preferred() -> None:
    installed = ["llava:7b", "moondream:latest"]
    assert pick_vision_model(installed, preferred="moondream") == "moondream:latest"


def test_pick_vision_model_none_without_vision() -> None:
    assert pick_vision_model(["qwen2.5-coder:7b", "llama3.2:3b"]) is None


def test_describe_mockup_uses_cache_and_chat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mockups = tmp_path / "mockups"
    mockups.mkdir()
    png = mockups / "home.png"
    # Minimal valid-ish PNG header bytes (content does not matter for encode).
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    events: List[Dict[str, Any]] = []
    chat_calls = {"n": 0}

    monkeypatch.setattr(
        "ia_platform.visual_engine.vision.list_ollama_models",
        lambda host, timeout=8: ["llava:7b"],
    )

    def fake_chat(**kwargs: Any) -> str:
        chat_calls["n"] += 1
        assert kwargs["model"] == "llava:7b"
        assert kwargs["image_b64"]
        return "## Visão geral\n- tela dark premium\n## Layout\n- sidebar + main"

    monkeypatch.setattr(
        "ia_platform.visual_engine.vision.ollama_chat_with_image",
        fake_chat,
    )

    first = describe_mockup(
        tmp_path,
        "mockups/home.png",
        host="http://127.0.0.1:11434",
        on_event=events.append,
    )
    assert first["ok"] is True
    assert "sidebar" in first["spec"]
    assert first["cached"] is False
    assert first["model"] == "llava:7b"
    assert chat_calls["n"] == 1
    assert any(e["type"] == "vision.started" for e in events)
    assert any(e["type"] == "vision.completed" for e in events)

    cache_dir = tmp_path / ".agent" / "vision-cache"
    assert cache_dir.is_dir()
    assert list(cache_dir.glob("*.json"))

    events.clear()
    second = describe_mockup(
        tmp_path,
        "mockups/home.png",
        host="http://127.0.0.1:11434",
        on_event=events.append,
    )
    assert second["ok"] is True
    assert second["cached"] is True
    assert chat_calls["n"] == 1  # no second Ollama call
    assert any(e["type"] == "vision.cached" for e in events)


def test_describe_mockup_skips_without_vision_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mockups = tmp_path / "mockups"
    mockups.mkdir()
    (mockups / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    monkeypatch.setattr(
        "ia_platform.visual_engine.vision.list_ollama_models",
        lambda host, timeout=8: ["qwen2.5-coder:7b"],
    )
    result = describe_mockup(tmp_path, "mockups/x.png")
    assert result["ok"] is False
    assert "visão" in result["error"].lower() or "vision" in result["error"].lower()


def test_describe_mockup_missing_file(tmp_path: Path) -> None:
    result = describe_mockup(tmp_path, "mockups/missing.png")
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_parse_and_format_structured_vision() -> None:
    from ia_platform.visual_engine.vision import format_vision_spec_for_goal, parse_vision_payload

    raw = json.dumps(
        {
            "overview": "IDE dark premium",
            "style": "dark",
            "layout": ["sidebar esquerda", "main chat"],
            "colors": {"background": "#0b0f14", "accent": "#3b82f6"},
            "priorities": ["1. sidebar", "2. tipografia"],
        }
    )
    parsed = parse_vision_payload(raw)
    assert parsed["structured"]["style"] == "dark"
    assert "#0b0f14" in parsed["spec"]
    packed = format_vision_spec_for_goal(parsed["structured"])
    assert "Cores" in packed
    assert "sidebar esquerda" in packed


def test_prepare_image_bytes_passthrough(tmp_path: Path) -> None:
    from ia_platform.visual_engine.vision import prepare_image_bytes

    png = tmp_path / "tiny.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    data, meta = prepare_image_bytes(png)
    assert data.startswith(b"\x89PNG")
    assert meta["resized"] is False
