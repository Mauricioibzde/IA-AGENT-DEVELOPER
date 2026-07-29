"""Main autonomous agent loop with auto-validation and multi-step execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from .config import AgentConfig
from .context_manager import ContextManager
from .executor import Executor
from .logging_config import AgentLogger
from .memory import AgentMemory
from .models import AgentReport, FinalStatus, Plan, ReflectionStatus, Task, TaskStatus, ValidationResult
from .ollama_client import OllamaClient
from .planner import Planner
from .project_index import ProjectIndex
from .prompts import executor_prompt, system_prompt
from .reflector import Reflector
from .tools import build_default_registry
from .validator import Validator


class CodingAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.logger = AgentLogger(config)
        self.client = OllamaClient(config, self.logger)
        self.memory = AgentMemory(config.workspace, enabled=config.use_memory)
        self.index = ProjectIndex(config.workspace)
        self.registry = build_default_registry(include_git=config.use_git)
        self.executor = Executor(self.registry, config, self.logger)
        self.planner = Planner(self.client, config.planner_model)
        self.reflector = Reflector(self.client, config.reflection_model)
        self.context_manager = ContextManager(config)
        self.validator = Validator(config, self.index)
        self.seen_signatures: Set[str] = set()
        self.analyzed_files: List[str] = []
        self.errors: List[str] = []
        self.fixed_errors: List[str] = []
        self.completed_tasks: List[str] = []
        self.all_validations: List[ValidationResult] = []

    def run(self, goal: str) -> AgentReport:
        self.config.workspace.mkdir(parents=True, exist_ok=True)
        self.logger.info("agent_start", message=f"Goal: {goal}")

        # Index project.
        self.index.build()
        self.memory.update_project_summary(self.index.summary(limit=20)[:1500])
        self.memory.add_event("user_request", goal)

        # Establish baseline (what was already failing before we changed anything).
        baseline: List[ValidationResult] = []
        if not self.config.plan_only and not self.config.dry_run:
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
        plan = self.planner.create_plan(goal, self.index.summary())
        self.logger.info("plan_created", message=plan.summary or plan.goal, tasks=len(plan.tasks))
        self.memory.add_event("plan", plan.summary or plan.goal, {"tasks": [t.id for t in plan.tasks]})

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

        while steps < self.config.max_steps:
            task = self._next_task(plan)
            if task is None:
                break
            steps += 1
            task.status = TaskStatus.RUNNING
            task.attempts += 1
            self.logger.info("agent_step", message=f"Step {steps}/{self.config.max_steps}: [{task.id}] {task.title}")

            # Build context with auto-read files.
            context = self.context_manager.build(
                goal=goal,
                task=task,
                project_index=self.index,
                memory=self.memory,
                errors=self.errors[-5:],
            )
            prompt = executor_prompt(
                goal, task, self.registry, context,
                previous_results=None,
            )

            try:
                model_text = self.client.complete(
                    prompt,
                    model=self.config.coder_model,
                    system=system_prompt(str(self.config.workspace)),
                )
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"LLM error: {exc}")
                task.status = TaskStatus.FAILED
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    self.logger.error("consecutive_failures", message="3 LLM failures in a row, stopping")
                    break
                continue

            calls = self.executor.parse_calls(model_text)
            if not calls:
                final_answer = model_text
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.append(task.title)
                break

            # Detect no-progress loops.
            signature = self._signature(task.id, calls)
            no_progress = signature in self.seen_signatures
            self.seen_signatures.add(signature)

            # Execute tools.
            results, finished = self.executor.run_calls(calls)
            self.memory.add_event("tools", f"{task.id}: {len(results)} tools", {"tools": [r["tool"] for r in results]})
            consecutive_failures = 0

            # Track analyzed files.
            for rel in task.relevant_files:
                if rel not in self.analyzed_files:
                    self.analyzed_files.append(rel)

            if finished:
                final_answer = results[-1]["result"].get("answer", "")
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.append(task.title)
                break

            # Auto-validate after filesystem writes.
            validation_results: List[ValidationResult] = []
            wrote_files = self.executor.had_writes_this_step(results)

            if task.validation_commands:
                validation_results = [self.validator.run_one(cmd) for cmd in task.validation_commands]
            elif wrote_files:
                quick_checks = self.validator.discover_commands()[:2]
                if quick_checks:
                    validation_results = [self.validator.run_one(cmd) for cmd in quick_checks]

            if any(r.get("result", {}).get("ok") is False for r in results) and not validation_results:
                validation_results = self.validator.run_all()[:2]

            self.all_validations.extend(validation_results)
            validation_summary = self.validator.summarize(validation_results)
            for item in validation_results:
                if not item.success and item.category == "introduced":
                    self.errors.append(f"{item.command}: {item.stderr[:200]}")

            # Reflect.
            decision = self.reflector.reflect(
                task,
                json.dumps(results, ensure_ascii=False)[:4000],
                validation_summary,
                no_progress=no_progress,
            )
            self.logger.info("reflection", message=f"{decision.status.value}: {decision.analysis[:120]}")
            self.memory.add_event("reflection", decision.analysis[:300], {"status": decision.status.value})

            # Act on reflection.
            if decision.status == ReflectionStatus.FINISH:
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.append(task.title)
                final_answer = decision.next_action or final_answer
                if not self._next_task(plan):
                    break
                continue

            if decision.status == ReflectionStatus.CONTINUE:
                all_ok = all(r.get("result", {}).get("ok", False) for r in results)
                validations_ok = all(v.success for v in validation_results) if validation_results else True
                if all_ok and validations_ok:
                    task.status = TaskStatus.COMPLETED
                    self.completed_tasks.append(task.title)
                elif task.attempts >= task.max_attempts:
                    task.status = TaskStatus.FAILED
                continue

            if decision.status == ReflectionStatus.RETRY:
                if task.attempts >= task.max_attempts:
                    task.status = TaskStatus.FAILED
                    self.errors.append(f"Task {task.id} exhausted retries: {decision.analysis[:200]}")
                else:
                    task.status = TaskStatus.PENDING
                continue

            if decision.status == ReflectionStatus.REPLAN or decision.should_replan:
                plan = self.planner.update_plan(plan, decision.analysis or "replan")
                task.status = TaskStatus.PENDING
                self.logger.info("replan", message="Plan updated after reflection")
                continue

            if decision.status == ReflectionStatus.ROLLBACK:
                task.status = TaskStatus.FAILED
                self.errors.append(f"Rollback requested: {decision.analysis[:200]}")
                continue

            if decision.status in {ReflectionStatus.ABORT, ReflectionStatus.ASK_USER}:
                task.status = TaskStatus.BLOCKED if decision.status == ReflectionStatus.ASK_USER else TaskStatus.FAILED
                self.errors.append(decision.analysis[:300])
                break

        return self._build_report(goal, plan, final_answer)

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
        blob = json.dumps({"task": task_id, "calls": calls}, sort_keys=True, ensure_ascii=False)
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

    def _build_report(self, goal: str, plan: Plan, final_answer: str) -> AgentReport:
        failed_tasks = [t for t in plan.tasks if t.status == TaskStatus.FAILED]
        blocked_tasks = [t for t in plan.tasks if t.status == TaskStatus.BLOCKED]
        pending = [t for t in plan.tasks if t.status in {TaskStatus.PENDING, TaskStatus.RUNNING}]

        # Final compile check for Python.
        if any(f.language == "python" for f in self.index.files) and not self.config.dry_run:
            final_check = self.validator.run_one("python -m compileall .")
            self.all_validations.append(final_check)

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
