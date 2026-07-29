"""Structured models for the local coding agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypedDict


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReflectionStatus(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    REPLAN = "replan"
    ROLLBACK = "rollback"
    ASK_USER = "ask_user"
    FINISH = "finish"
    ABORT = "abort"


class FinalStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    DRY_RUN_COMPLETED = "DRY_RUN_COMPLETED"


class ToolCallDict(TypedDict, total=False):
    tool: str
    name: str
    action: str
    args: Dict[str, Any]


@dataclass
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    validation_commands: List[str] = field(default_factory=list)
    relevant_files: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    attempts: int = 0
    max_attempts: int = 3
    notes: str = ""


@dataclass
class Plan:
    goal: str
    summary: str
    tasks: List[Task] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"ok": self.ok, **self.data}
        if self.error:
            payload["error"] = self.error
        if self.dry_run:
            payload["dry_run"] = True
        return payload


@dataclass
class ToolDefinition:
    name: str
    description: str
    argument_schema: Dict[str, object]
    risk_level: RiskLevel
    mutating: bool
    requires_confirmation: bool
    handler: Callable[..., ToolResult]


@dataclass
class ProjectFile:
    path: str
    language: Optional[str]
    size: int
    imports: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    is_config: bool = False
    is_test: bool = False


@dataclass
class ValidationResult:
    command: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    category: str = "unknown"  # introduced | pre_existing | missing_tool | timeout | environment | code


@dataclass
class ReflectionDecision:
    status: ReflectionStatus
    analysis: str
    next_action: str
    relevant_files: List[str] = field(default_factory=list)
    should_replan: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    evidence: List[str] = field(default_factory=list)


@dataclass
class AgentReport:
    status: FinalStatus
    goal: str
    summary: str
    completed_tasks: List[str] = field(default_factory=list)
    analyzed_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    created_files: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    validations: List[ValidationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    fixed_errors: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)

    def render(self) -> str:
        def bullets(items: List[str], empty: str) -> List[str]:
            return [f"- {item}" for item in items] if items else [empty]

        lines = [
            f"Status: {self.status.value}",
            f"Objetivo: {self.goal}",
            f"Resumo: {self.summary}",
            "",
            "Tarefas concluídas:",
            *bullets(self.completed_tasks, "- (nenhuma)"),
            "",
            "Arquivos analisados:",
            *bullets(self.analyzed_files, "- (nenhum)"),
            "",
            "Arquivos modificados:",
            *bullets(self.modified_files, "- (nenhum)"),
            "",
            "Arquivos criados:",
            *bullets(self.created_files, "- (nenhum)"),
            "",
            "Comandos executados:",
            *bullets(self.commands, "- (nenhum)"),
            "",
            "Testes / validações:",
        ]
        if self.validations:
            for v in self.validations:
                mark = "OK" if v.success else "FAIL"
                lines.append(f"- [{mark}] {v.command} (exit={v.exit_code}, {v.duration_seconds:.2f}s)")
        else:
            lines.append("- (nenhuma)")
        lines.extend(
            [
                "",
                "Erros encontrados:",
                *bullets(self.errors, "- (nenhum)"),
                "",
                "Erros corrigidos:",
                *bullets(self.fixed_errors, "- (nenhum)"),
                "",
                "Riscos / limitações:",
                *bullets(self.risks, "- (nenhum)"),
                "",
                "Próximos passos:",
                *bullets(self.next_steps, "- (nenhum)"),
            ]
        )
        return "\n".join(lines)


@dataclass
class MemoryEvent:
    kind: str
    summary: str
    payload: Dict[str, Any] = field(default_factory=dict)
