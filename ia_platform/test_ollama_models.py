"""Tests for Ollama model manager pull helpers."""

from __future__ import annotations

import io
import json

from ia_platform.ollama_models import OllamaModelManager


class _FakeResponse(io.BytesIO):
    def __init__(self, lines: list[str]):
        payload = "\n".join(lines).encode("utf-8")
        super().__init__(payload)

    def __iter__(self):
        return io.BytesIO(self.getvalue()).__iter__()


def test_pull_reports_ollama_error(monkeypatch) -> None:
    mgr = OllamaModelManager("http://127.0.0.1:11434")
    events: list[dict] = []

    def fake_urlopen(req, timeout=3600):
        return _FakeResponse([json.dumps({"error": "model not found"})])

    monkeypatch.setattr("ia_platform.ollama_models.urllib.request.urlopen", fake_urlopen)
    result = mgr.pull("missing:7b", on_event=events.append)
    assert result["ok"] is False
    assert "model not found" in result["error"]
    assert events[-1]["type"] == "error"


def test_pull_marks_success_on_status(monkeypatch) -> None:
    mgr = OllamaModelManager("http://127.0.0.1:11434")
    events: list[dict] = []

    def fake_urlopen(req, timeout=3600):
        return _FakeResponse(
            [
                json.dumps({"status": "downloading", "completed": 50, "total": 100}),
                json.dumps({"status": "success"}),
            ]
        )

    monkeypatch.setattr("ia_platform.ollama_models.urllib.request.urlopen", fake_urlopen)
    result = mgr.pull("demo:1b", on_event=events.append)
    assert result["ok"] is True
    assert any(ev.get("type") == "progress" and ev.get("percent") == 50 for ev in events)
