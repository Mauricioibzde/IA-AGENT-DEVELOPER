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
            last["error"] = str(exc)
            if on_event:
                on_event({"type": "error", "error": str(exc)})
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
                event = self._normalize_pull_event(model, data)
                last.update(event)
                if on_event:
                    on_event(event)
                if data.get("status") == "success" or (data.get("completed") and data.get("total") and data["completed"] >= data["total"]):
                    last["ok"] = True
        finally:
            response.close()

        if "error" not in last and last.get("status") != "error":
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
