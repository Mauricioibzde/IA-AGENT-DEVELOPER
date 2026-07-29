"""Main autonomous agent loop with auto-validation and multi-step execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .checkpoint import RunCheckpoint
from .config import AgentConfig
from .context_manager import ContextManager
from .executor import Executor
from .logging_config import AgentLogger
from .memory import AgentMemory
from .models import AgentReport, FinalStatus, Plan, ReflectionStatus, Task, TaskStatus, ValidationResult
from .ollama_client import OllamaClient
from .planner import Planner
from .project_index import ProjectIndex
from .prompts import executor_prompt, final_report_prompt, system_prompt
from .reflector import Reflector
from .tools import build_default_registry
from .validator import Validator
from .web_scaffold import (
    looks_like_fastapi_goal,
    looks_like_offline_scaffold_goal,
    looks_like_plain_web_goal,
    looks_like_react_goal,
    validate_plain_web,
    write_fastapi_app,
    write_plain_web_app,
    write_react_app,
)


class CodingAgent:
    def __init__(self, config: AgentConfig, event_sink: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.config = config
        self.event_sink = event_sink
        self.logger = AgentLogger(config)
        self.client = OllamaClient(config, self.logger)
        self.memory = AgentMemory(config.workspace, enabled=config.use_memory)
        self.index = ProjectIndex(config.workspace)
        self.registry = build_default_registry(include_git=config.use_git)
        self.checkpoint = RunCheckpoint(config.workspace, config.run_id or "anonymous")
        self.executor = Executor(self.registry, config, self.logger, checkpoint=self.checkpoint)
        self.planner = Planner(self.client, config.planner_model)
        self.reflector = Reflector(self.client, config.reflection_model)
        self.context_manager = ContextManager(config)
        self.validator = Validator(config, self.index)
        self.seen_signatures: Set[str] = set()
        self.signature_hits: Dict[str, int] = {}
        self.analyzed_files: List[str] = []
        self.errors: List[str] = []
        self.fixed_errors: List[str] = []
        self.completed_tasks: List[str] = []
        self.all_validations: List[ValidationResult] = []
        self._deps_ensured = False
    def _event(self, kind: str, **fields: Any) -> None:
        if not self.event_sink:
            return
        try:
            self.event_sink({"type": kind, **fields})
        except Exception:  # noqa: BLE001
            pass

    def _is_cancelled(self) -> bool:
        return bool(self.config.cancel_check and self.config.cancel_check())

    def _cancelled_report(self, goal: str, plan: Optional[Plan] = None) -> AgentReport:
        self.logger.info("agent_cancelled", message="Run cancelled by user")
        self._event("cancelled")
        summary = "Execução cancelada pelo usuário."
        if plan:
            summary += f"\n\nTarefas concluídas: {len(self.completed_tasks)}"
        return AgentReport(
            status=FinalStatus.CANCELLED,
            goal=goal,
            summary=summary,
            completed_tasks=self.completed_tasks,
            analyzed_files=self.analyzed_files[:30],
            created_files=self.executor.created_files,
            modified_files=self.executor.modified_files,
        )

    def run(self, goal: str, conversation_context: str = "") -> AgentReport:
        self.config.workspace.mkdir(parents=True, exist_ok=True)
        self.logger.info("agent_start", message=f"Goal: {goal}")
        self._event("started", goal=goal, run_id=self.config.run_id)

        if self._is_cancelled():
            return self._cancelled_report(goal)

        # Index project.
        self.index.build()
        self.memory.update_project_summary(self.index.summary(limit=20)[:1500])
        self.memory.add_event("user_request", goal)

        # If Ollama is offline, still deliver tiny HTML/CSS/JS apps deterministically.
        ollama_ok = False
        try:
            ollama_ok = bool(self.client.check_available(timeout=2))
        except Exception:  # noqa: BLE001
            ollama_ok = False
        if not ollama_ok and looks_like_offline_scaffold_goal(goal) and not self.config.plan_only:
            return self._deterministic_scaffold(goal, reason="Ollama offline — scaffold aplicado")

        # Establish baseline (what was already failing before we changed anything).
        baseline: List[ValidationResult] = []
        if not self.config.plan_only and not self.config.dry_run and not self._should_skip_baseline():
            if self._is_cancelled():
                return self._cancelled_report(goal)
            try:
                baseline = self.validator.establish_baseline()
                self.all_validations.extend(baseline)
                if baseline:
                    self.logger.info(
                        "baseline",
                        message=f"{sum(1 for v in baseline if v.success)}/{len(baseline)} passed",
                    )
            except Exception as exc:  # noqa: BLE001
                self.logger.warn("baseline_failed", message=str(exc))

        # Create plan.
        self._event("planning", message="Analisando projeto e criando plano...")
        if self._is_cancelled():
            return self._cancelled_report(goal)
        index_summary = self.index.summary()
        relevant = self.index.relevant_summary(goal, limit=10)
        if relevant:
            index_summary = f"{index_summary}\n\n{relevant}"
        plan = self.planner.create_plan(
            goal,
            index_summary,
            index=self.index,
            conversation=conversation_context or "",
        )
        for task in plan.tasks:
            task.max_attempts = self.config.max_task_attempts
        self.logger.info("plan_created", message=plan.summary or plan.goal, tasks=len(plan.tasks))
        self.memory.add_event("plan", plan.summary or plan.goal, {"tasks": [t.id for t in plan.tasks]})
        self._event(
            "plan",
            summary=plan.summary or plan.goal,
            task_count=len(plan.tasks),
            tasks=[{"id": t.id, "title": t.title} for t in plan.tasks[:8]],
        )

        if self.config.plan_only:
            return AgentReport(
                status=FinalStatus.SUCCESS if not self.config.dry_run else FinalStatus.DRY_RUN_COMPLETED,
                goal=goal,
                summary="Plan-only mode.\n" + self._render_plan(plan),
                completed_tasks=[t.title for t in plan.tasks],
                analyzed_files=[f.path for f in self.index.files[:30]],
                next_steps=["Re-run without --plan-only to execute"],
                risks=plan.risks,
            )

        # Execute tasks.
        steps = 0
        final_answer = ""
        consecutive_failures = 0
        current_task_id: Optional[str] = None
        last_results_json = ""
        last_validation = ""
        last_diffs = ""
        step_had_failures = False
        pending_no_progress = False

        while steps < self.config.max_steps:
            if self._is_cancelled():
                return self._cancelled_report(goal, plan)

            task = self._next_task(plan)
            if task is None:
                break

            if task.id != current_task_id:
                current_task_id = task.id
                last_results_json = ""
                last_validation = ""
                last_diffs = ""
                step_had_failures = False
                pending_no_progress = False

            steps += 1
            task.status = TaskStatus.RUNNING
            task.attempts += 1
            self.logger.info("agent_step", message=f"Step {steps}/{self.config.max_steps}: [{task.id}] {task.title}")
            self._event(
                "step",
                step=steps,
                max_steps=self.config.max_steps,
                task_id=task.id,
                task_title=task.title,
            )

            # Build context with feedback from prior attempts on this task.
            context = self.context_manager.build(
                goal=goal,
                task=task,
                project_index=self.index,
                memory=self.memory,
                errors=self.errors[-5:],
                validation=last_validation,
                previous_results=last_results_json or None,
                conversation=conversation_context,
            )
            self.executor.mark_reads(self.context_manager.last_read_paths)

            prompt = executor_prompt(
                goal,
                task,
                self.registry,
                context,
                workspace=str(self.config.workspace),
                previous_results=last_results_json or None,
                recent_diffs=last_diffs or None,
                no_progress=pending_no_progress,
            )

            try:
                sys_msg = system_prompt(str(self.config.workspace))
                if self.event_sink:
                    def _on_chunk(text: str) -> None:
                        self._event("llm_chunk", text=text)

                    model_text = self.client.stream_chat(
                        [{"role": "user", "content": prompt}],
                        model=self.config.coder_model,
                        system=sys_msg,
                        on_chunk=_on_chunk,
                        cancel_check=self.config.cancel_check,
                    )
                else:
                    model_text = self.client.complete(
                        prompt,
                        model=self.config.coder_model,
                        system=sys_msg,
                    )
                if self._is_cancelled():
                    return self._cancelled_report(goal, plan)
            except Exception as exc:  # noqa: BLE001
                if self._is_cancelled() or "cancelled" in str(exc).lower():
                    return self._cancelled_report(goal, plan)
                self.errors.append(f"LLM error: {exc}")
                self._event("error", message=str(exc))
                task.status = TaskStatus.FAILED
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    if looks_like_offline_scaffold_goal(goal) and not self.executor.created_files:
                        return self._deterministic_scaffold(
                            goal,
                            reason="Modelo indisponível após falhas — scaffold aplicado",
                        )
                    self.logger.error("consecutive_failures", message="3 LLM failures in a row, stopping")
                    break
                continue

            calls = self.executor.parse_calls(model_text)
            if not calls:
                repair_text = self._repair_tool_calls(model_text)
                if repair_text:
                    calls = self.executor.parse_calls(repair_text)
            if not calls:
                self.errors.append(f"Task {task.id}: model returned no valid tool calls")
                last_results_json = json.dumps(
                    [{"error": "no_valid_tool_calls", "raw": model_text[:800]}],
                    ensure_ascii=False,
                )
                if task.attempts >= task.max_attempts:
                    task.status = TaskStatus.FAILED
                else:
                    task.status = TaskStatus.PENDING
                continue

            # Detect no-progress loops (identical tool+args signatures).
            signature = self._signature(task.id, calls)
            hit_count = self.signature_hits.get(signature, 0) + 1
            self.signature_hits[signature] = hit_count
            no_progress = hit_count >= 2
            self.seen_signatures.add(signature)

            # Execute tools.
            self._event(
                "tools_start",
                count=len(calls),
                tools=[str(c.get("tool") or c.get("name") or c.get("action") or "?") for c in calls],
            )
            results, finished = self.executor.run_calls(calls)
            last_results_json = self._format_tool_results(results)
            last_diffs = "\n".join(self.executor.step_diffs[-3:])
            step_had_failures = any(not r.get("result", {}).get("ok", False) for r in results)

            self.memory.add_event(
                "tools",
                f"{task.id}: {len(results)} tools",
                {"tools": [r["tool"] for r in results], "ok": sum(1 for r in results if r.get("result", {}).get("ok"))},
            )
            consecutive_failures = 0
            self._event(
                "tools",
                count=len(results),
                tools=[r.get("tool", "?") for r in results],
                ok=sum(1 for r in results if r.get("result", {}).get("ok", False)),
            )

            # Track analyzed files and refresh index after writes.
            for rel in task.relevant_files:
                if rel not in self.analyzed_files:
                    self.analyzed_files.append(rel)

            wrote_files = self.executor.had_writes_this_step(results)
            if wrote_files:
                changed_paths = self._paths_from_results(results)
                self.context_manager.invalidate_many(changed_paths)
                self.index.build()
                self.memory.update_project_summary(self.index.summary(limit=20)[:1500])
                self._event(
                    "files_changed",
                    paths=changed_paths[:12],
                    created=list(dict.fromkeys(self.executor.created_files))[-8:],
                    modified=list(dict.fromkeys(self.executor.modified_files))[-8:],
                )

            if finished:
                final_answer = results[-1]["result"].get("answer", "")
                # Do not accept `final` before validation — fall through to checks.
                intend_finish = True
            else:
                intend_finish = False

            # Auto-validate after filesystem writes (and before accepting final).
            validation_results: List[ValidationResult] = []

            # Install Node deps once before npm validations so React builds can succeed.
            needs_npm = False
            if task.validation_commands:
                needs_npm = any("npm" in c or "vite" in c or "npx" in c for c in task.validation_commands)
            elif (wrote_files or intend_finish) and self.index.package_scripts:
                needs_npm = True
            if needs_npm and not self._deps_ensured:
                install_result = self.validator.ensure_node_dependencies()
                self._deps_ensured = True
                if install_result is not None:
                    validation_results.append(install_result)
                    self._event(
                        "validation",
                        count=1,
                        ok=1 if install_result.success else 0,
                        summary=f"npm install: {'ok' if install_result.success else 'fail'}",
                    )

            if task.validation_commands:
                self._event("validation_start", commands=task.validation_commands[:3])
                validation_results.extend([self.validator.run_one(cmd) for cmd in task.validation_commands])
            elif wrote_files or intend_finish:
                quick_checks = self.validator.discover_commands()[:2]
                if not quick_checks and looks_like_plain_web_goal(goal):
                    problems = validate_plain_web(self.config.workspace)
                    if problems:
                        validation_results.append(
                            ValidationResult(
                                command="validate_plain_web",
                                success=False,
                                exit_code=1,
                                stdout="",
                                stderr="; ".join(problems),
                                duration_seconds=0.0,
                                category="introduced",
                            )
                        )
                    else:
                        validation_results.append(
                            ValidationResult(
                                command="validate_plain_web",
                                success=True,
                                exit_code=0,
                                stdout="ok",
                                stderr="",
                                duration_seconds=0.0,
                                category="code",
                            )
                        )
                elif quick_checks:
                    self._event("validation_start", commands=quick_checks)
                    validation_results.extend([self.validator.run_one(cmd) for cmd in quick_checks])

            if step_had_failures and not validation_results:
                self._event("validation_start", commands=["auto"])
                validation_results.extend(self.validator.run_all()[:2])

            self.all_validations.extend(validation_results)
            validation_summary = self.validator.summarize(validation_results)
            if validation_results:
                self._event(
                    "validation",
                    count=len(validation_results),
                    ok=sum(1 for v in validation_results if v.success),
                    summary=validation_summary[:240],
                )
            last_validation = validation_summary
            for item in validation_results:
                if not item.success and item.category == "introduced":
                    self.errors.append(f"{item.command}: {item.stderr[:200] or item.stdout[:200]}")

            # Reflect.
            decision = self.reflector.reflect(
                task,
                last_results_json[:4000],
                validation_summary,
                no_progress=no_progress,
                no_progress_count=hit_count if no_progress else 0,
            )
            self.logger.info("reflection", message=f"{decision.status.value}: {decision.analysis[:120]}")
            self.memory.add_event("reflection", decision.analysis[:300], {"status": decision.status.value})
            self.memory.record_decision(decision.next_action[:200] if decision.next_action else decision.analysis[:200])
            self._event(
                "reflection",
                status=decision.status.value,
                analysis=decision.analysis[:240],
            )

            if decision.relevant_files:
                task.relevant_files = list(dict.fromkeys(task.relevant_files + decision.relevant_files))
            if decision.next_action:
                task.notes = decision.next_action[:500]

            all_ok = all(r.get("result", {}).get("ok", False) for r in results)
            validations_ok = all(v.success for v in validation_results) if validation_results else True
            introduced_fail = any(
                (not v.success and v.category == "introduced") for v in validation_results
            )

            if intend_finish:
                if all_ok and validations_ok and not introduced_fail and not step_had_failures:
                    task.status = TaskStatus.COMPLETED
                    self.completed_tasks.append(task.title)
                    if self.errors:
                        self.fixed_errors.append(f"Recovered on task {task.id}")
                    break
                # Reject premature final when validation failed.
                task.status = TaskStatus.PENDING
                self.errors.append(
                    f"final rejeitado: validação pendente/falhou ({validation_summary[:180]})"
                )
                last_results_json = json.dumps(
                    [
                        {
                            "tool": "final",
                            "ok": False,
                            "error": "Validação obrigatória falhou antes de concluir",
                            "validation": validation_summary[:500],
                        }
                    ],
                    ensure_ascii=False,
                )
                continue

            if step_had_failures is False and self.errors and all_ok and validations_ok:
                fix_note = f"Task {task.id} succeeded after prior errors"
                if fix_note not in self.fixed_errors:
                    self.fixed_errors.append(fix_note)

            # Act on reflection.
            if decision.status == ReflectionStatus.FINISH:
                if all_ok and validations_ok and not introduced_fail:
                    task.status = TaskStatus.COMPLETED
                    self.completed_tasks.append(task.title)
                    final_answer = decision.next_action or final_answer
                    if not self._next_task(plan):
                        break
                else:
                    task.status = TaskStatus.PENDING
                continue

            if decision.status == ReflectionStatus.CONTINUE:
                # CONTINUE means more work remains on this task — never mark completed.
                if task.attempts >= task.max_attempts:
                    task.status = TaskStatus.FAILED
                else:
                    task.status = TaskStatus.PENDING
                continue

            if decision.status == ReflectionStatus.RETRY:
                if task.attempts >= task.max_attempts:
                    task.status = TaskStatus.FAILED
                    self.errors.append(f"Task {task.id} exhausted retries: {decision.analysis[:200]}")
                else:
                    task.status = TaskStatus.PENDING
                continue

            if decision.status == ReflectionStatus.REPLAN or decision.should_replan:
                plan = self.planner.update_plan(plan, decision.analysis or "replan", index=self.index)
                for t in plan.tasks:
                    if t.max_attempts == 3:
                        t.max_attempts = self.config.max_task_attempts
                task.status = TaskStatus.PENDING
                self.logger.info("replan", message="Plan updated after reflection")
                continue

            if decision.status == ReflectionStatus.ROLLBACK:
                self._rollback_recent_changes()
                self.index.build()
                task.status = TaskStatus.PENDING
                self.errors.append(f"Rollback applied: {decision.analysis[:200]}")
                last_results_json = json.dumps([{"action": "rollback", "analysis": decision.analysis[:300]}])
                continue

            if decision.status in {ReflectionStatus.ABORT, ReflectionStatus.ASK_USER}:
                task.status = TaskStatus.BLOCKED if decision.status == ReflectionStatus.ASK_USER else TaskStatus.FAILED
                self.errors.append(decision.analysis[:300])
                break

        return self._build_report(goal, plan, final_answer)

    def _repair_tool_calls(self, model_text: str) -> str:
        try:
            tool_names = ", ".join(sorted(t.name for t in self.registry.list_tools())[:40])
            return self.client.complete(
                "Your previous response was not valid JSON tool call(s).\n"
                "Return ONLY one JSON object or JSON array of tool calls. No markdown, no prose.\n"
                'Schema: {"tool":"<name>","args":{...}} or [{"tool":"...","args":{...}}, ...]\n'
                f"Allowed tools include: {tool_names}\n\n"
                f"Previous output:\n{model_text[:2500]}",
                model=self.config.coder_model,
                temperature=0,
            )
        except Exception:  # noqa: BLE001
            return ""

    def _format_tool_results(self, results: List[Dict[str, object]]) -> str:
        compact = []
        budget = 3500
        used = 0
        for item in results:
            res = item.get("result", {})
            if not isinstance(res, dict):
                continue
            entry: Dict[str, object] = {"tool": item.get("tool"), "ok": res.get("ok")}
            if res.get("error"):
                entry["error"] = str(res.get("error"))[:400]
            if res.get("path"):
                entry["path"] = res.get("path")
            if res.get("stdout"):
                entry["stdout"] = str(res.get("stdout"))[-800:]
            if res.get("stderr"):
                entry["stderr"] = str(res.get("stderr"))[-800:]
            if res.get("diff"):
                entry["diff"] = str(res.get("diff"))[:600]
            # Preserve payloads the model needs for the next step.
            if res.get("content") is not None:
                entry["content"] = str(res.get("content"))[:2500]
            if res.get("items") is not None:
                items = res.get("items")
                if isinstance(items, list):
                    entry["items"] = items[:80]
                else:
                    entry["items"] = items
            if res.get("matches") is not None:
                matches = res.get("matches")
                if isinstance(matches, list):
                    entry["matches"] = matches[:30]
                else:
                    entry["matches"] = matches
            if res.get("files") is not None:
                files = res.get("files")
                if isinstance(files, list):
                    entry["files"] = [str(f) for f in files[:40]]
                else:
                    entry["files"] = files
            if res.get("total_lines") is not None:
                entry["total_lines"] = res.get("total_lines")
            if res.get("answer") is not None:
                entry["answer"] = str(res.get("answer"))[:500]
            blob = json.dumps(entry, ensure_ascii=False)
            if used + len(blob) > budget and compact:
                entry = {
                    "tool": entry.get("tool"),
                    "ok": entry.get("ok"),
                    "error": entry.get("error"),
                    "path": entry.get("path"),
                    "truncated": True,
                }
            compact.append(entry)
            used += len(json.dumps(entry, ensure_ascii=False))
        return json.dumps(compact, ensure_ascii=False, indent=2)

    def _paths_from_results(self, results: List[Dict[str, object]]) -> List[str]:
        from .security import to_rel_path

        paths: List[str] = []
        for item in results:
            res = item.get("result", {})
            if isinstance(res, dict):
                if res.get("path"):
                    paths.append(to_rel_path(self.config.workspace, str(res["path"])))
                if res.get("dst"):
                    paths.append(to_rel_path(self.config.workspace, str(res["dst"])))
                files = res.get("files")
                if isinstance(files, list):
                    for f in files[:40]:
                        paths.append(to_rel_path(self.config.workspace, str(f)))
        return list(dict.fromkeys(paths))

    def _rollback_recent_changes(self) -> None:
        if self.checkpoint and self.checkpoint.entries:
            result = self.checkpoint.restore()
            self._event(
                "rollback",
                restored=result.get("restored") or [],
                removed=result.get("removed") or [],
            )
            # Reset executor tracking to match restored workspace.
            self.executor.created_files.clear()
            self.executor.modified_files.clear()
            self.executor.step_diffs.clear()
            return
        for path in reversed(self.executor.modified_files[-5:]):
            self.executor.run_calls([{"tool": "rollback_file", "args": {"path": path}}])
        self.executor.step_diffs.clear()

    def _next_task(self, plan: Plan) -> Optional[Task]:
        done = {t.id for t in plan.tasks if t.status == TaskStatus.COMPLETED}
        for task in plan.tasks:
            if task.status in {TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.BLOCKED}:
                continue
            if task.status == TaskStatus.FAILED and task.attempts >= task.max_attempts:
                continue
            if all(dep in done for dep in task.dependencies):
                return task
        return None

    def _signature(self, task_id: str, calls: List[Dict[str, object]]) -> str:
        normalized = []
        for call in calls:
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            arg_digest = ""
            if isinstance(args, dict):
                # Hash arg values so different content on same path is not "stuck".
                try:
                    raw = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
                except TypeError:
                    raw = str(sorted(args.items()))
                # Cap huge content payloads but keep enough to distinguish edits.
                if len(raw) > 1200:
                    raw = raw[:600] + f"...len={len(raw)}..." + raw[-200:]
                arg_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
            normalized.append(
                {
                    "task": task_id,
                    "tool": call.get("tool"),
                    "path": args.get("path") if isinstance(args, dict) else None,
                    "command": args.get("command") if isinstance(args, dict) else None,
                    "arg_digest": arg_digest,
                }
            )
        blob = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _render_plan(self, plan: Plan) -> str:
        lines = [f"Goal: {plan.goal}", f"Summary: {plan.summary}", "Tasks:"]
        for task in plan.tasks:
            dep = f" (depends: {', '.join(task.dependencies)})" if task.dependencies else ""
            lines.append(f"- [{task.id}] {task.title}{dep}: {task.description}")
        if plan.risks:
            lines.append("\nRisks:")
            for risk in plan.risks:
                lines.append(f"- {risk}")
        return "\n".join(lines)

    def _deterministic_scaffold(self, goal: str, *, reason: str) -> AgentReport:
        """Create a starter app without calling the LLM (plain web / React / FastAPI)."""
        self._event("planning", message=reason)
        if self.config.dry_run:
            kind = (
                "react"
                if looks_like_react_goal(goal)
                else ("fastapi" if looks_like_fastapi_goal(goal) else "html")
            )
            return AgentReport(
                status=FinalStatus.DRY_RUN_COMPLETED,
                goal=goal,
                summary=f"{reason}\nScaffold planejado: {kind}",
                next_steps=["Re-run without dry-run to write files"],
            )

        if looks_like_react_goal(goal):
            from ia_platform.project_templates import react_vite_files

            for rel in react_vite_files("tmp").keys():
                self.checkpoint.snapshot_before(rel)
            created, title = write_react_app(self.config.workspace, goal)
            kind_label = "React + Vite"
            next_steps = ["npm install && npm run dev", "Abrir Preview ao vivo", "Melhorar visual"]
        elif looks_like_fastapi_goal(goal):
            from local_agent.web_scaffold import fastapi_files

            for rel in fastapi_files().keys():
                self.checkpoint.snapshot_before(rel)
            created, title = write_fastapi_app(self.config.workspace, goal)
            kind_label = "FastAPI"
            next_steps = ["pip install -r requirements.txt", "uvicorn main:app --reload", "pytest -q"]
        else:
            from local_agent.web_scaffold import plain_web_files

            for rel in plain_web_files().keys():
                self.checkpoint.snapshot_before(rel)
            created, title = write_plain_web_app(self.config.workspace, goal)
            kind_label = "HTML/CSS/JS"
            next_steps = ["Abrir Preview", "Melhorar visual", "Adicionar seção"]
            problems = validate_plain_web(self.config.workspace)
            if problems:
                self.errors.extend(problems)

        self.executor.created_files.extend(created)
        self.completed_tasks.append(f"Criar {title}")
        self.index.build(use_cache=False)
        self._event("files_changed", paths=created, created=created, modified=[])
        self._event(
            "plan",
            summary=reason,
            task_count=1,
            tasks=[{"id": "task-1", "title": f"Criar {title}"}],
        )
        summary = (
            f"{reason}\n\n"
            f"Criei **{title}** ({kind_label}). "
            f"Arquivos: {', '.join(f'`{c}`' for c in created[:8])}."
        )
        return AgentReport(
            status=FinalStatus.SUCCESS,
            goal=goal,
            summary=summary,
            completed_tasks=self.completed_tasks,
            analyzed_files=created,
            created_files=list(dict.fromkeys(self.executor.created_files)),
            modified_files=list(dict.fromkeys(self.executor.modified_files)),
            next_steps=next_steps,
            risks=[],
        )

    def _deterministic_plain_web(self, goal: str, *, reason: str) -> AgentReport:
        return self._deterministic_scaffold(goal, reason=reason)

    def _should_skip_baseline(self) -> bool:
        """Skip heavy baseline when Node deps are not installed yet."""
        if self.index.package_scripts and not (self.config.workspace / "node_modules").is_dir():
            return True
        return False

    def _report_facts(self, goal: str, plan: Plan, status: FinalStatus) -> str:
        failed = [t.title for t in plan.tasks if t.status == TaskStatus.FAILED]
        pending = [t.title for t in plan.tasks if t.status in {TaskStatus.PENDING, TaskStatus.RUNNING}]
        validation_lines = [
            f"- {v.command}: {'ok' if v.success else 'fail'} ({v.category})"
            for v in self.all_validations[-8:]
        ]
        lines = [
            f"Status: {status.value}",
            f"Completed tasks: {', '.join(self.completed_tasks) or 'none'}",
            f"Created files: {', '.join(self.executor.created_files) or 'none'}",
            f"Modified files: {', '.join(self.executor.modified_files) or 'none'}",
            f"Failed tasks: {', '.join(failed) or 'none'}",
            f"Pending tasks: {', '.join(pending) or 'none'}",
            f"Errors: {'; '.join(self.errors[-5:]) or 'none'}",
            f"Fixed errors: {'; '.join(self.fixed_errors[-3:]) or 'none'}",
            "Validations:",
            *(validation_lines or ["- none"]),
        ]
        return "\n".join(lines)

    def _summarize_with_llm(self, goal: str, plan: Plan, status: FinalStatus, fallback: str) -> str:
        if self.config.dry_run or self.config.plan_only or status == FinalStatus.CANCELLED:
            return fallback
        if self._is_cancelled():
            return fallback
        stats = getattr(self.client, "stats", None)
        if stats and stats.get("budget_remaining", 1) <= 0:
            return fallback
        facts = self._report_facts(goal, plan, status)
        try:
            summary = self.client.complete(
                final_report_prompt(goal, facts),
                model=self.config.reflection_model,
                temperature=0.2,
            )
            if summary.strip() and not self._is_cancelled():
                return summary.strip()
        except Exception as exc:  # noqa: BLE001
            if "cancelled" in str(exc).lower():
                return fallback
            self.logger.warn("final_report_failed", message=str(exc))
        return fallback

    def _build_report(self, goal: str, plan: Plan, final_answer: str) -> AgentReport:
        failed_tasks = [t for t in plan.tasks if t.status == TaskStatus.FAILED]
        blocked_tasks = [t for t in plan.tasks if t.status == TaskStatus.BLOCKED]
        pending = [t for t in plan.tasks if t.status in {TaskStatus.PENDING, TaskStatus.RUNNING}]

        # Final smoke checks before declaring success.
        if not self.config.dry_run:
            has_python = any(f.language == "python" for f in self.index.files)
            has_pkg = (self.config.workspace / "package.json").is_file()
            has_index = (self.config.workspace / "index.html").is_file()
            if has_python:
                final_check = self.validator.run_one("python -m compileall .")
                self.all_validations.append(final_check)
            if has_index and not has_pkg:
                problems = validate_plain_web(self.config.workspace)
                self.all_validations.append(
                    ValidationResult(
                        command="validate_plain_web",
                        success=not problems,
                        exit_code=0 if not problems else 1,
                        stdout="ok" if not problems else "",
                        stderr="; ".join(problems),
                        duration_seconds=0.0,
                        category="code" if not problems else "introduced",
                    )
                )
            elif has_pkg and (self.config.workspace / "node_modules").is_dir():
                scripts = self.index.package_scripts or {}
                if "build" in scripts:
                    build = self.validator.run_one("npm run build")
                    self.all_validations.append(build)

        introduced_failures = [v for v in self.all_validations if not v.success and v.category == "introduced"]

        if self.config.dry_run:
            status = FinalStatus.DRY_RUN_COMPLETED
        elif blocked_tasks:
            status = FinalStatus.BLOCKED
        elif introduced_failures or (failed_tasks and not self.completed_tasks):
            status = FinalStatus.FAILED
        elif failed_tasks or pending or self.errors:
            status = FinalStatus.PARTIAL_SUCCESS
        else:
            status = FinalStatus.SUCCESS

        summary = final_answer or plan.summary or "Execução concluída."
        if status != FinalStatus.SUCCESS and not final_answer:
            summary = f"{summary}\nEstado final: {status.value}"
        summary = self._summarize_with_llm(goal, plan, status, summary)

        # Persist memory.
        all_files = list(dict.fromkeys(self.executor.created_files + self.executor.modified_files))[:30]
        self.memory.remember_files(all_files)
        if self.errors:
            issues = self.memory.long_term.setdefault("known_issues", [])
            for err in self.errors[-5:]:
                if err not in issues:
                    issues.append(err)
            self.memory.save()

        return AgentReport(
            status=status,
            goal=goal,
            summary=summary,
            completed_tasks=self.completed_tasks,
            analyzed_files=list(dict.fromkeys(self.analyzed_files + [f.path for f in self.index.files[:20]])),
            modified_files=list(dict.fromkeys(self.executor.modified_files)),
            created_files=list(dict.fromkeys(self.executor.created_files)),
            commands=list(dict.fromkeys(self.executor.commands)),
            validations=self.all_validations[-12:],
            errors=self.errors,
            fixed_errors=self.fixed_errors,
            risks=plan.risks,
            next_steps=[
                "Revisar diff/arquivos gerados",
                "Usar Desfazer execução se precisar reverter",
                "Rodar a suite de testes do projeto alvo",
            ],
        )


def run_agent(
    prompt: str,
    workspace: str,
    model: str = "qwen2.5-coder:7b",
    max_steps: int = 12,
    *,
    dry_run: bool = False,
    verbose: bool = False,
    **kwargs: object,
) -> str:
    """Backward-compatible functional API."""
    config = AgentConfig.from_args(
        workspace,
        model=model,
        max_steps=max_steps,
        dry_run=dry_run,
        verbose=verbose,
        planner_model=str(kwargs.get("planner_model") or model),
        reflection_model=str(kwargs.get("reflection_model") or model),
        plan_only=bool(kwargs.get("plan_only", False)),
        no_memory=bool(kwargs.get("no_memory", False)),
        no_git=bool(kwargs.get("no_git", False)),
        debug=bool(kwargs.get("debug", False)),
    )
    report = CodingAgent(config).run(prompt)
    return report.render()
