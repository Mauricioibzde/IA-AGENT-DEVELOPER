"""Reflection component for retry/replan/finish decisions."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .json_utils import loads_json_lenient
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
        no_progress_count: int = 0,
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
            if no_progress_count <= 2:
                return ReflectionDecision(
                    status=ReflectionStatus.RETRY,
                    analysis="Repeated identical tool pattern — change approach before replanning",
                    next_action="Use different tools/args, read more context, or split the edit",
                    should_replan=False,
                    risk_level=RiskLevel.MEDIUM,
                    evidence=["repeated identical tool signature"],
                )
            return ReflectionDecision(
                status=ReflectionStatus.REPLAN,
                analysis="No progress detected after repeated identical tool/error pattern",
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
        data = loads_json_lenient(text)
        if isinstance(data, dict) and "status" in data:
            return data
        # Fallback greedy match for partially repaired blobs.
        match = re.search(r"\{.*\}", text or "", re.S)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) and "status" in parsed else None

    def _from_dict(self, data: Dict[str, Any]) -> ReflectionDecision:
        status_raw = str(data.get("status", "")).lower().strip()
        if not status_raw:
            # Empty status from model → treat like heuristic later if needed; default continue.
            status = ReflectionStatus.CONTINUE
        else:
            try:
                status = ReflectionStatus(status_raw)
            except ValueError:
                # Invalid status token — prefer finish only when caller re-checks; keep CONTINUE
                # and let agent use tool/validation signals, but map common aliases.
                aliases = {
                    "done": ReflectionStatus.FINISH,
                    "complete": ReflectionStatus.FINISH,
                    "completed": ReflectionStatus.FINISH,
                    "ok": ReflectionStatus.FINISH,
                    "success": ReflectionStatus.FINISH,
                }
                status = aliases.get(status_raw, ReflectionStatus.CONTINUE)
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
        failed = (
            "FAIL" in validation_summary
            or '"ok": false' in tool_results.lower()
            or '"ok":false' in tool_results.lower()
        )
        if not failed:
            # Successful tools/validation → finish the task (CONTINUE would loop forever).
            return ReflectionDecision(
                status=ReflectionStatus.FINISH,
                analysis="Tools and validation look successful — completing this task",
                next_action="Proceed to the next task or finalize",
                risk_level=RiskLevel.LOW,
            )
        return ReflectionDecision(
            status=ReflectionStatus.RETRY,
            analysis="Failure detected in tools/validation",
            next_action="Inspect error output and apply a corrective edit",
            should_replan=False,
            risk_level=RiskLevel.MEDIUM,
            evidence=[validation_summary[:200], tool_results[:200]],
        )
