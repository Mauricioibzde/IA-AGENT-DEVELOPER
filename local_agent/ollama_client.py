"""Ollama HTTP client with chat/generate fallback, retries, and streaming support."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, Optional

from .config import AgentConfig
from .logging_config import AgentLogger


class OllamaError(RuntimeError):
    """Raised when Ollama cannot be reached or returns an invalid payload."""


class OllamaClient:
    def __init__(self, config: AgentConfig, logger: Optional[AgentLogger] = None) -> None:
        self.config = config
        self.logger = logger
        self.call_count = 0
        self.total_chars_received = 0

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 180,
        retries: int = 2,
        *,
        system: Optional[str] = None,
    ) -> str:
        model_name = model or self.config.coder_model
        self.call_count += 1
        if self.call_count > self.config.max_model_calls:
            raise OllamaError(f"Model call budget exceeded ({self.config.max_model_calls})")

        if system:
            messages = [{"role": "system", "content": system}, *messages]

        last_error: Exception | None = None
        cancel_check = self.config.cancel_check
        for attempt in range(retries + 1):
            if cancel_check and cancel_check():
                raise OllamaError("cancelled")
            try:
                content = self._chat_once(messages, model_name, temperature, timeout)
                self.total_chars_received += len(content)
                return self._strip_thinking(content)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if self.logger:
                    self.logger.warn("llm_retry", message=str(exc), attempt=attempt + 1, model=model_name)
                time.sleep(min(2 ** attempt, 4))
        raise OllamaError(f"Ollama request failed after {retries + 1} attempts: {last_error}")

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 300,
        *,
        system: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> str:
        """Stream chat response chunks; returns full stripped content."""
        model_name = model or self.config.coder_model
        self.call_count += 1
        if self.call_count > self.config.max_model_calls:
            raise OllamaError(f"Model call budget exceeded ({self.config.max_model_calls})")

        if system:
            messages = [{"role": "system", "content": system}, *messages]

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        req = urllib.request.Request(
            f"{self.config.ollama_host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(req, timeout=timeout)
        except Exception as exc:
            raise OllamaError(f"Streaming chat failed: {exc}") from exc

        parts: List[str] = []
        try:
            for line in response:
                if cancel_check and cancel_check():
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                message = data.get("message") or {}
                chunk = message.get("content") or data.get("response") or ""
                if chunk:
                    parts.append(chunk)
                    self.total_chars_received += len(chunk)
                    if on_chunk:
                        on_chunk(chunk)
                if data.get("done"):
                    break
        finally:
            response.close()

        content = self._strip_thinking("".join(parts))
        if cancel_check and cancel_check():
            raise OllamaError("cancelled")
        if not content:
            raise OllamaError("Ollama returned an empty streaming response")
        return content

    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 180,
        *,
        system: Optional[str] = None,
    ) -> str:
        cancel_check = self.config.cancel_check
        if cancel_check and cancel_check():
            raise OllamaError("cancelled")
        if cancel_check:
            return self.stream_chat(
                [{"role": "user", "content": prompt}],
                model=model,
                temperature=temperature,
                timeout=timeout,
                system=system,
                cancel_check=cancel_check,
            )
        return self.chat(
            [{"role": "user", "content": prompt}],
            model=model,
            temperature=temperature,
            timeout=timeout,
            system=system,
        )

    def stream_complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 300,
    ) -> Iterator[str]:
        """Yield response chunks for real-time terminal output."""
        model_name = model or self.config.coder_model
        self.call_count += 1
        if self.call_count > self.config.max_model_calls:
            raise OllamaError(f"Model call budget exceeded ({self.config.max_model_calls})")

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        req = urllib.request.Request(
            f"{self.config.ollama_host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(req, timeout=timeout)
        except Exception as exc:
            raise OllamaError(f"Streaming request failed: {exc}") from exc

        try:
            for line in response:
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                chunk = data.get("response", "")
                if chunk:
                    self.total_chars_received += len(chunk)
                    yield chunk
                if data.get("done"):
                    break
        finally:
            response.close()

    def check_available(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            req = urllib.request.Request(f"{self.config.ollama_host}/api/tags")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            req = urllib.request.Request(f"{self.config.ollama_host}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception:
            return []

    def _chat_once(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        timeout: int,
    ) -> str:
        host = self.config.ollama_host
        chat_payload: Dict[str, Any] = {
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

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """Remove <think>...</think> blocks that some models produce."""
        import re
        cleaned = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S)
        return cleaned.strip() or text.strip()

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

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "call_count": self.call_count,
            "total_chars_received": self.total_chars_received,
            "budget_remaining": max(0, self.config.max_model_calls - self.call_count),
        }
