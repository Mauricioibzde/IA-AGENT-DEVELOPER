"""Ollama HTTP client with chat/generate fallback and retries."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .config import AgentConfig
from .logging_config import AgentLogger


class OllamaError(RuntimeError):
    """Raised when Ollama cannot be reached or returns an invalid payload."""


class OllamaClient:
    def __init__(self, config: AgentConfig, logger: Optional[AgentLogger] = None) -> None:
        self.config = config
        self.logger = logger
        self.call_count = 0

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 180,
        retries: int = 2,
    ) -> str:
        model_name = model or self.config.coder_model
        self.call_count += 1
        if self.call_count > self.config.max_model_calls:
            raise OllamaError(f"Model call budget exceeded ({self.config.max_model_calls})")

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return self._chat_once(messages, model_name, temperature, timeout)
            except Exception as exc:  # noqa: BLE001 - retry boundary
                last_error = exc
                if self.logger:
                    self.logger.warn("llm_retry", message=str(exc), attempt=attempt + 1)
                time.sleep(min(2 ** attempt, 4))
        raise OllamaError(f"Ollama request failed: {last_error}")

    def complete(self, prompt: str, model: Optional[str] = None, temperature: float = 0.1, timeout: int = 180) -> str:
        return self.chat(
            [{"role": "user", "content": prompt}],
            model=model,
            temperature=temperature,
            timeout=timeout,
        )

    def _chat_once(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        timeout: int,
    ) -> str:
        host = self.config.ollama_host
        chat_payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            data = self._post(f"{host}/api/chat", chat_payload, timeout=timeout)
            message = data.get("message") or {}
            content = (message.get("content") or data.get("response") or "").strip()
            if content:
                if self.logger:
                    self.logger.debug("llm_chat", message=f"{len(content)} chars", model=model)
                return content
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OllamaError) as exc:
            if self.logger:
                self.logger.debug("llm_chat_fallback", message=str(exc))

        prompt = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        data = self._post(
            f"{host}/api/generate",
            {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": temperature}},
            timeout=timeout,
        )
        content = str(data.get("response", "")).strip()
        if not content:
            raise OllamaError("Ollama returned an empty response")
        if self.logger:
            self.logger.debug("llm_generate", message=f"{len(content)} chars", model=model)
        return content

    def _post(self, url: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaError(f"Invalid JSON from Ollama: {exc}") from exc
        if not isinstance(data, dict):
            raise OllamaError("Unexpected Ollama payload type")
        return data
