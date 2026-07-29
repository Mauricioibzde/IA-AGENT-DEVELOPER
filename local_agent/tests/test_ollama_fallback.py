"""OOM / HTTP 500 model fallback in OllamaClient."""

from __future__ import annotations

from local_agent.config import AgentConfig
from local_agent.ollama_client import OllamaClient, OllamaError, is_likely_oom_error


def test_is_likely_oom_error_detects_500_and_memory() -> None:
    assert is_likely_oom_error("HTTP Error 500: Internal Server Error")
    assert is_likely_oom_error("Chat falhou: insufficient memory")
    assert is_likely_oom_error("não cabe na memória deste computador")
    assert not is_likely_oom_error("connection refused")


def test_chat_falls_back_to_smaller_model(monkeypatch) -> None:
    cfg = AgentConfig.from_args(".", model="qwen2.5-coder:32b", no_memory=True)
    client = OllamaClient(cfg)
    calls: list[str] = []

    def fake_list() -> list[str]:
        return ["qwen2.5-coder:32b", "deepseek-coder:6.7b"]

    def fake_chat_once(messages, model, temperature, timeout):
        calls.append(model)
        if model == "qwen2.5-coder:32b":
            raise OllamaError(
                "Chat falhou no modelo 'qwen2.5-coder:32b': HTTP Error 500: Internal Server Error"
            )
        return "ok from smaller"

    monkeypatch.setattr(client, "list_models", fake_list)
    monkeypatch.setattr(client, "_chat_once", fake_chat_once)

    out = client.chat([{"role": "user", "content": "hi"}], model="qwen2.5-coder:32b", retries=1)
    assert out == "ok from smaller"
    assert calls[0] == "qwen2.5-coder:32b"
    assert "deepseek-coder:6.7b" in calls
    assert client.active_model == "deepseek-coder:6.7b"
    assert client.config.coder_model == "deepseek-coder:6.7b"
    event = client.consume_fallback_event()
    assert event == {"from": "qwen2.5-coder:32b", "to": "deepseek-coder:6.7b"}


def test_minimal_safe_plan_page_section_is_plain_web() -> None:
    from local_agent.prompts import minimal_safe_plan

    plan = minimal_safe_plan(
        "Adicione uma nova seção relevante na página principal com bom layout e texto em português."
    )
    assert "HTML/CSS/JS" in plan["summary"]
    assert plan["tasks"][0]["relevant_files"] == ["index.html", "style.css", "app.js"]
