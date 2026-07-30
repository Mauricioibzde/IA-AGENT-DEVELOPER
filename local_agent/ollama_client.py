"""Ollama HTTP client with chat/generate fallback, retries, and streaming support."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, Optional

from .config import AgentConfig
from .logging_config import AgentLogger


class OllamaError(RuntimeError):
    """Raised when Ollama cannot be reached or returns an invalid payload."""


def _read_http_error_body(exc: urllib.error.HTTPError, limit: int = 400) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def is_likely_oom_error(message: str) -> bool:
    """True when the error likely means the model could not be loaded in memory."""
    lower = (message or "").lower()
    tokens = (
        "insufficient memory",
        "out of memory",
        "can't allocate",
        "cannot allocate",
        "failed to allocate",
        "oom",
        "não cabe na memória",
        "nao cabe na memoria",
        "memória insuficiente",
        "memoria insuficiente",
        "http error 500",
        "internal server error",
    )
    return any(token in lower for token in tokens)


def _format_ollama_http_error(exc: urllib.error.HTTPError, model_name: Optional[str] = None) -> str:
    detail = _read_http_error_body(exc)
    lower = detail.lower()
    model = (model_name or "").strip() or "modelo"
    if any(
        token in lower
        for token in (
            "insufficient memory",
            "out of memory",
            "can't allocate",
            "cannot allocate",
            "failed to allocate",
            "oom",
        )
    ) or (exc.code == 500 and not detail.strip()):
        return (
            f"O modelo '{model}' está instalado, mas não cabe na memória deste computador "
            f"(Ollama sem RAM/VRAM suficiente para carregar). "
            f"Escolha Auto ou um modelo menor (ex.: 7B / 6.7B). {detail}".strip()
        )
    if exc.code == 500:
        return (
            f"O modelo '{model}' falhou no Ollama (HTTP 500). "
            f"Costuma ser falta de memória ao carregar o modelo. "
            f"Escolha Auto ou um modelo menor (ex.: 7B). {detail}".strip()
        )
    if exc.code == 404:
        return (
            f"Modelo '{model}' não encontrado no Ollama (404). "
            f"Escolha outro modelo ou use Auto. {detail}".strip()
        )
    return f"HTTP Error {exc.code}: {exc.reason}" + (f" — {detail}" if detail else "")


class OllamaClient:
    def __init__(self, config: AgentConfig, logger: Optional[AgentLogger] = None) -> None:
        self.config = config
        self.logger = logger
        self.call_count = 0
        self.total_chars_received = 0
        # When a large model OOMs, stick to a smaller installed model for the rest of the run.
        self.active_model: Optional[str] = None
        self.last_fallback: Optional[Dict[str, str]] = None
        self._fallback_attempted_for: set[str] = set()

    def resolve_model(self, model: Optional[str] = None) -> str:
        return self.active_model or model or self.config.coder_model

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
        model_name = self.resolve_model(model)
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
                if is_likely_oom_error(str(exc)):
                    fallback = self._activate_fallback(model_name)
                    if fallback:
                        model_name = fallback
                        continue
                    # Do not burn retries on a model that cannot load.
                    break
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
        model_name = self.resolve_model(model)
        self.call_count += 1
        if self.call_count > self.config.max_model_calls:
            raise OllamaError(f"Model call budget exceeded ({self.config.max_model_calls})")

        if system:
            messages = [{"role": "system", "content": system}, *messages]

        try:
            content = self._stream_chat_once(
                messages,
                model_name,
                temperature,
                timeout,
                on_chunk=on_chunk,
                cancel_check=cancel_check,
            )
        except Exception as stream_exc:
            if cancel_check and cancel_check():
                raise OllamaError("cancelled") from stream_exc
            if self.logger:
                self.logger.warn("llm_stream_fallback", message=str(stream_exc), model=model_name)

            # OOM/500: switch model before non-stream retry so we don't thrash the same giant model.
            if is_likely_oom_error(str(stream_exc)):
                fallback = self._activate_fallback(model_name)
                if fallback:
                    model_name = fallback

            try:
                content = self._chat_once(messages, model_name, temperature, timeout)
            except Exception as fallback_exc:
                if is_likely_oom_error(str(fallback_exc)):
                    next_model = self._activate_fallback(model_name)
                    if next_model:
                        try:
                            content = self._chat_once(messages, next_model, temperature, timeout)
                        except Exception as final_exc:
                            raise OllamaError(self._format_chat_failure(next_model, final_exc)) from final_exc
                    else:
                        raise OllamaError(self._format_chat_failure(model_name, fallback_exc)) from fallback_exc
                else:
                    raise OllamaError(self._format_chat_failure(model_name, fallback_exc)) from fallback_exc
            if on_chunk and content:
                on_chunk(content)

        content = self._strip_thinking(content)
        if cancel_check and cancel_check():
            raise OllamaError("cancelled")
        if not content:
            raise OllamaError("Ollama returned an empty streaming response")
        return content

    def _format_chat_failure(self, model_name: str, exc: Exception) -> str:
        msg = str(exc)
        if msg.startswith(f"Chat falhou no modelo '{model_name}'"):
            return msg
        return (
            f"Chat falhou no modelo '{model_name}': {exc}. "
            "Escolha Auto ou um modelo que caiba na memória deste PC."
        )

    def _activate_fallback(self, failed_model: str) -> Optional[str]:
        failed = (failed_model or "").strip()
        if not failed:
            return None
        if failed.lower() in self._fallback_attempted_for:
            return self.active_model if self.active_model and self.active_model.lower() != failed.lower() else None
        self._fallback_attempted_for.add(failed.lower())

        try:
            from ia_platform.model_catalog import pick_smaller_fallback_model
        except Exception:
            pick_smaller_fallback_model = None  # type: ignore[assignment]

        installed = self.list_models()
        fallback = None
        if pick_smaller_fallback_model:
            fallback = pick_smaller_fallback_model(failed, installed)
        if not fallback:
            # Lightweight local ranking if catalog import is unavailable.
            for name in installed:
                lower = name.lower()
                if lower == failed.lower() or "embed" in lower or lower.endswith("-base"):
                    continue
                if any(tag in lower for tag in ("7b", "6.7b", "3b", "1.5b", "8b")):
                    fallback = name
                    break
            if not fallback:
                for name in installed:
                    if name.lower() != failed.lower() and "embed" not in name.lower():
                        fallback = name
                        break
        if not fallback or fallback.lower() == failed.lower():
            return None

        self.active_model = fallback
        self.config.model = fallback
        self.config.coder_model = fallback
        self.config.planner_model = fallback
        self.config.reflection_model = fallback
        self.last_fallback = {"from": failed, "to": fallback}
        if self.logger:
            self.logger.warn("llm_model_fallback", from_model=failed, to_model=fallback)
        return fallback

    def consume_fallback_event(self) -> Optional[Dict[str, str]]:
        event = self.last_fallback
        self.last_fallback = None
        return event

    def _stream_chat_once(
        self,
        messages: List[Dict[str, str]],
        model_name: str,
        temperature: float,
        timeout: int,
        *,
        on_chunk: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> str:
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
        except urllib.error.HTTPError as exc:
            raise OllamaError(
                f"Chat falhou no modelo '{model_name}': {_format_ollama_http_error(exc, model_name)}"
            ) from exc
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

        return "".join(parts)

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
        model_name = self.resolve_model(model)
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

    def check_available(self, timeout: int = 5) -> bool:
        """Return True if Ollama is reachable."""
        try:
            req = urllib.request.Request(f"{self.config.ollama_host}/api/tags")
            with urllib.request.urlopen(req, timeout=timeout):
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
            # Propagate OOM/500 immediately — retrying /api/generate with the same model rarely helps.
            if isinstance(exc, OllamaError) and is_likely_oom_error(str(exc)):
                raise

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
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            model_name = str(payload.get("model") or "")
            raise OllamaError(_format_ollama_http_error(exc, model_name)) from exc
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
            "active_model": self.active_model or self.config.coder_model,
        }
