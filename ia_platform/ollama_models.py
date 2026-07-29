"""Ollama model pull/list helpers for the Forge platform."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, Optional


class OllamaModelManager:
    def __init__(self, host: str) -> None:
        self.host = host.rstrip("/")

    def list_installed(self) -> List[Dict[str, Any]]:
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []
        models = []
        for item in data.get("models") or []:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or ""
            size = item.get("size") or 0
            models.append(
                {
                    "name": name,
                    "size_gb": round(size / (1024**3), 2) if size else 0,
                    "modified": item.get("modified_at"),
                    "digest": (item.get("digest") or "")[:16],
                }
            )
        return models

    def list_names(self) -> List[str]:
        return [m["name"] for m in self.list_installed() if m.get("name")]

    def has_model(self, model: str) -> bool:
        from ia_platform.model_catalog import _is_model_installed

        return _is_model_installed(model, self.list_names())

    def pull(
        self,
        model: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout: int = 3600,
    ) -> Dict[str, Any]:
        payload = {"name": model, "stream": True}
        req = urllib.request.Request(
            f"{self.host}/api/pull",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        last: Dict[str, Any] = {"ok": False, "model": model}
        try:
            response = urllib.request.urlopen(req, timeout=timeout)
        except Exception as exc:
            message = str(exc)
            if "Connection refused" in message or "Errno 111" in message:
                message = "Ollama offline — execute 'ollama serve' em outro terminal"
            last["error"] = message
            if on_event:
                on_event({"type": "error", "error": message, "ollama_offline": True})
            return last

        try:
            for line in response:
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if data.get("error"):
                    message = str(data.get("error"))
                    last = {"ok": False, "model": model, "error": message, "status": "error"}
                    if on_event:
                        on_event({"type": "error", "error": message, "model": model})
                    return last
                event = self._normalize_pull_event(model, data)
                last.update(event)
                if on_event:
                    on_event(event)
                if data.get("status") == "success":
                    last["ok"] = True
        finally:
            response.close()

        if last.get("status") == "success":
            last["ok"] = True
        elif "error" not in last and last.get("completed") and last.get("total") and last["completed"] >= last["total"]:
            last["ok"] = True
        return last

    def pull_iter(self, model: str, timeout: int = 3600) -> Iterator[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        def collect(event: Dict[str, Any]) -> None:
            events.append(event)

        result = self.pull(model, on_event=collect, timeout=timeout)
        for event in events:
            yield event
        yield {"type": "done", **result}

    @staticmethod
    def _normalize_pull_event(model: str, data: Dict[str, Any]) -> Dict[str, Any]:
        completed = data.get("completed") or 0
        total = data.get("total") or 0
        percent = round((completed / total) * 100, 1) if total else None
        return {
            "type": "progress",
            "model": model,
            "status": data.get("status") or "",
            "completed": completed,
            "total": total,
            "percent": percent,
            "digest": data.get("digest"),
        }
