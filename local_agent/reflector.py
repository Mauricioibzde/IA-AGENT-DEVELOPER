"""Reflection component for retry/replan/finish decisions."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .models import ReflectionDecision, ReflectionStatus, RiskLevel, Task
from .ollama_client import OllamaClient
from .prompts import reflector_prompt


class Reflector:
    def __init__(self, client: OllamaClient, model: str) -> None:
        self.client = client
        self.model = model

    def reflect(
        self,
        task: Task,
        tool_results: str,
        validation_summary: str,
        *,
        no_progress: bool = False,
    ) -> ReflectionDecision:
        if task.attempts >= task.max_attempts:
            return ReflectionDecision(
                status=ReflectionStatus.ABORT,
                analysis="Task attempt budget exhausted",
                next_action="Stop current task and report failure",
                should_replan=True,
                risk_level=RiskLevel.HIGH,
                evidence=[f"attempts={task.attempts}"],
            )
        if no_progress:
            return ReflectionDecision(
                status=ReflectionStatus.REPLAN,
                analysis="No progress detected (repeated tool/error)",
                next_action="Change strategy and replan remaining work",
                should_replan=True,
                risk_level=RiskLevel.MEDIUM,
                evidence=["repeated identical failure signature"],
            )

        prompt = reflector_prompt(task, tool_results, validation_summary, task.attempts)
        try:
            raw = self.client.complete(prompt, model=self.model, temperature=0.1)
            data = self._parse(raw)
            if data is None:
                return self._heuristic(task, tool_results, validation_summary)
            return self._from_dict(data)
        except Exception:
            return self._heuristic(task, tool_results, validation_summary)

    def _parse(self, text: str) -> Optional[Dict[str, Any]]:
        content = text.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "status" in data:
                return data
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) and "status" in data else None

    def _from_dict(self, data: Dict[str, Any]) -> ReflectionDecision:
        status_raw = str(data.get("status", "continue")).lower()
        try:
            status = ReflectionStatus(status_raw)
        except ValueError:
            status = ReflectionStatus.CONTINUE
        risk_raw = str(data.get("risk_level", "low")).lower()
        try:
            risk = RiskLevel(risk_raw)
        except ValueError:
            risk = RiskLevel.LOW
        return ReflectionDecision(
            status=status,
            analysis=str(data.get("analysis") or ""),
            next_action=str(data.get("next_action") or ""),
            relevant_files=[str(x) for x in data.get("relevant_files") or []],
            should_replan=bool(data.get("should_replan")) or status == ReflectionStatus.REPLAN,
            risk_level=risk,
            evidence=[str(x) for x in data.get("evidence") or []],
        )

    def _heuristic(self, task: Task, tool_results: str, validation_summary: str) -> ReflectionDecision:
        failed = "FAIL" in validation_summary or '"ok": false' in tool_results.lower() or '"ok":false' in tool_results.lower()
        if not failed:
            return ReflectionDecision(
                status=ReflectionStatus.CONTINUE,
                analysis="No failure signals in latest results",
                next_action="Proceed to next task step",
            )
        return ReflectionDecision(
            status=ReflectionStatus.RETRY,
            analysis="Failure detected in tools/validation",
            next_action="Inspect error output and apply a corrective edit",
            should_replan=False,
            risk_level=RiskLevel.MEDIUM,
            evidence=[validation_summary[:200], tool_results[:200]],
        )
