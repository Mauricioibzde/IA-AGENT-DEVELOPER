"""Visual correction loop — compare → patch → recompare → accept/rollback."""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .patches import apply_patches, plan_heuristic_patches, rollback_patches

CompareFn = Callable[[], Dict[str, Any]]
PatchPlanFn = Callable[[Dict[str, Any]], List[Dict[str, Any]]]
EventFn = Callable[[Dict[str, Any]], None]


@dataclass
class CorrectionConfig:
    target_similarity: float = 0.95
    max_attempts: int = 5
    min_improvement: float = 0.005
    stagnation_limit: int = 2
    worsen_epsilon: float = 0.002
    timeout_sec: float = 600.0
    allow_worsen_reasons: tuple = ()  # reserved for explicit exceptions


@dataclass
class CorrectionAttempt:
    attempt: int
    similarity: Optional[float]
    previous_similarity: Optional[float]
    status: str  # accepted | rolled_back | stagnated | cancelled | failed
    patches: int = 0
    comparison_id: str = ""
    checkpoint_id: str = ""
    notes: str = ""
    duration_ms: int = 0


@dataclass
class CorrectionJob:
    id: str
    project_id: str
    status: str = "queued"  # queued|running|completed|failed|cancelled
    config: CorrectionConfig = field(default_factory=CorrectionConfig)
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    best_similarity: Optional[float] = None
    current_similarity: Optional[float] = None
    baseline_similarity: Optional[float] = None
    improvement: Optional[float] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    cancel_requested: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "config": asdict(self.config),
            "attempts": list(self.attempts),
            "events": list(self.events[-80:]),
            "best_similarity": self.best_similarity,
            "current_similarity": self.current_similarity,
            "baseline_similarity": self.baseline_similarity,
            "improvement": self.improvement,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "cancel_requested": self.cancel_requested,
            "meta": dict(self.meta),
        }


class CorrectionLoop:
    """Synchronous correction loop with injectable compare/patch for tests."""

    def __init__(
        self,
        workspace: Path,
        *,
        compare_fn: CompareFn,
        plan_fn: Optional[PatchPlanFn] = None,
        apply_fn: Optional[Callable[[List[Dict[str, Any]], str], Dict[str, Any]]] = None,
        rollback_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
        on_event: Optional[EventFn] = None,
        config: Optional[CorrectionConfig] = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.compare_fn = compare_fn
        self.plan_fn = plan_fn or (lambda report: plan_heuristic_patches(report))
        self.apply_fn = apply_fn or (
            lambda patches, run_id: apply_patches(self.workspace, patches, run_id=run_id)
        )
        self.rollback_fn = rollback_fn or (lambda run_id: rollback_patches(self.workspace, run_id))
        self.on_event = on_event or (lambda _ev: None)
        self.config = config or CorrectionConfig()

    def _emit(self, job: CorrectionJob, typ: str, **payload: Any) -> None:
        ev = {"type": typ, "ts": time.time(), **payload}
        job.events.append(ev)
        self.on_event(ev)

    def run(self, job: CorrectionJob) -> CorrectionJob:
        cfg = self.config
        job.status = "running"
        started = time.time()
        self._emit(job, "correction.started", job_id=job.id)

        try:
            if job.cancel_requested:
                job.status = "cancelled"
                job.finished_at = time.time()
                self._emit(job, "correction.cancelled")
                return job
            self._emit(job, "comparison.processing", phase="baseline")
            baseline = self.compare_fn()
            if job.cancel_requested:
                job.status = "cancelled"
                job.finished_at = time.time()
                self._emit(job, "correction.cancelled")
                return job
            base_sim = _sim(baseline)
            job.baseline_similarity = base_sim
            job.best_similarity = base_sim
            job.current_similarity = base_sim
            self._emit(
                job,
                "comparison.completed",
                phase="baseline",
                similarity=base_sim,
                comparison_id=baseline.get("comparisonId"),
            )

            if base_sim is not None and base_sim >= cfg.target_similarity:
                job.status = "completed"
                job.improvement = 0.0
                job.finished_at = time.time()
                self._emit(job, "correction.completed", reason="already_at_target", similarity=base_sim)
                return job

            stagnant = 0
            previous = baseline
            prev_sim = base_sim if base_sim is not None else 0.0

            for attempt_no in range(1, cfg.max_attempts + 1):
                if job.cancel_requested:
                    job.status = "cancelled"
                    self._emit(job, "correction.cancelled")
                    break
                if time.time() - started > cfg.timeout_sec:
                    job.status = "failed"
                    job.error = "timeout"
                    self._emit(job, "comparison.failed", error="timeout")
                    break

                self._emit(job, "correction.planning", attempt=attempt_no)
                patches = self.plan_fn(previous if isinstance(previous, dict) else {})
                if not patches:
                    job.status = "completed"
                    self._emit(job, "correction.completed", reason="no_patches")
                    break

                checkpoint_id = f"corr-{job.id}-{attempt_no}"
                self._emit(job, "correction.patch_created", attempt=attempt_no, patches=len(patches))
                try:
                    apply_result = self.apply_fn(patches, checkpoint_id)
                except Exception as apply_exc:  # noqa: BLE001
                    attempt = CorrectionAttempt(
                        attempt=attempt_no,
                        similarity=prev_sim,
                        previous_similarity=prev_sim,
                        status="failed",
                        patches=len(patches),
                        checkpoint_id=checkpoint_id,
                        notes=f"apply failed: {apply_exc}",
                    )
                    job.attempts.append(asdict(attempt))
                    self._emit(job, "comparison.failed", error=str(apply_exc), attempt=attempt_no)
                    job.status = "failed"
                    job.error = str(apply_exc)
                    break
                if isinstance(apply_result, dict) and apply_result.get("ok") is False:
                    err = str(apply_result.get("error") or "apply returned ok=false")
                    attempt = CorrectionAttempt(
                        attempt=attempt_no,
                        similarity=prev_sim,
                        previous_similarity=prev_sim,
                        status="failed",
                        patches=len(patches),
                        checkpoint_id=checkpoint_id,
                        notes=err,
                    )
                    job.attempts.append(asdict(attempt))
                    self._emit(job, "comparison.failed", error=err, attempt=attempt_no)
                    # Soft-continue for transient busy; hard-fail otherwise.
                    if "busy" in err.lower():
                        stagnant += 1
                        if stagnant >= cfg.stagnation_limit:
                            job.status = "completed"
                            self._emit(job, "correction.completed", reason="stagnation_apply_busy")
                            break
                        continue
                    job.status = "failed"
                    job.error = err
                    break
                self._emit(
                    job,
                    "correction.applied",
                    attempt=attempt_no,
                    written=apply_result.get("written") or [],
                    kind=(apply_result.get("kind") if isinstance(apply_result, dict) else None),
                )

                t0 = time.time()
                if job.cancel_requested:
                    job.status = "cancelled"
                    self._emit(job, "correction.cancelled")
                    break
                self._emit(job, "correction.retesting", attempt=attempt_no)
                report = self.compare_fn()
                if job.cancel_requested:
                    job.status = "cancelled"
                    self._emit(job, "correction.cancelled")
                    break
                new_sim = _sim(report)
                duration_ms = int((time.time() - t0) * 1000)
                job.current_similarity = new_sim

                attempt = CorrectionAttempt(
                    attempt=attempt_no,
                    similarity=new_sim,
                    previous_similarity=prev_sim,
                    status="accepted",
                    patches=len(patches),
                    comparison_id=str(report.get("comparisonId") or ""),
                    checkpoint_id=checkpoint_id,
                    duration_ms=duration_ms,
                )

                if new_sim is None:
                    self.rollback_fn(checkpoint_id)
                    attempt.status = "failed"
                    attempt.notes = "compare returned no similarity"
                    job.attempts.append(asdict(attempt))
                    self._emit(job, "correction.rolled_back", attempt=attempt_no, reason="no_score")
                    break

                delta = new_sim - prev_sim
                if new_sim + cfg.worsen_epsilon < prev_sim:
                    self.rollback_fn(checkpoint_id)
                    attempt.status = "rolled_back"
                    attempt.notes = f"worsened by {-delta:.4f}"
                    job.attempts.append(asdict(attempt))
                    stagnant += 1
                    self._emit(
                        job,
                        "correction.rolled_back",
                        attempt=attempt_no,
                        similarity=new_sim,
                        previous=prev_sim,
                    )
                    if stagnant >= cfg.stagnation_limit:
                        job.status = "completed"
                        self._emit(job, "correction.completed", reason="stagnation_after_worsen")
                        break
                    continue

                if delta < cfg.min_improvement:
                    # Keep patch (neutral) but count stagnation; optional rollback on pure flatline.
                    stagnant += 1
                    attempt.status = "stagnated"
                    attempt.notes = f"improvement {delta:.4f} < {cfg.min_improvement}"
                    job.attempts.append(asdict(attempt))
                    previous = report
                    prev_sim = new_sim
                    if new_sim >= (job.best_similarity or 0):
                        job.best_similarity = new_sim
                    self._emit(
                        job,
                        "correction.improved",
                        attempt=attempt_no,
                        similarity=new_sim,
                        stagnated=True,
                    )
                    if stagnant >= cfg.stagnation_limit:
                        job.status = "completed"
                        self._emit(job, "correction.completed", reason="stagnation")
                        break
                else:
                    stagnant = 0
                    attempt.status = "accepted"
                    attempt.notes = f"improved by {delta:.4f}"
                    job.attempts.append(asdict(attempt))
                    previous = report
                    prev_sim = new_sim
                    job.best_similarity = max(job.best_similarity or 0.0, new_sim)
                    self._emit(
                        job,
                        "correction.improved",
                        attempt=attempt_no,
                        similarity=new_sim,
                        delta=delta,
                    )

                if new_sim >= cfg.target_similarity:
                    job.status = "completed"
                    self._emit(job, "correction.completed", reason="target_reached", similarity=new_sim)
                    break
            else:
                if job.status == "running":
                    job.status = "completed"
                    self._emit(job, "correction.completed", reason="max_attempts")

        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error = str(exc)
            self._emit(job, "comparison.failed", error=str(exc))

        if job.baseline_similarity is not None and job.best_similarity is not None:
            job.improvement = round(job.best_similarity - job.baseline_similarity, 6)
        job.finished_at = time.time()
        if job.status == "running":
            job.status = "completed"
        return job


def _sim(report: Dict[str, Any]) -> Optional[float]:
    if not isinstance(report, dict):
        return None
    val = report.get("similarity")
    if val is None and isinstance(report.get("report"), dict):
        val = report["report"].get("similarity")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


class CorrectionManager:
    """In-memory + disk-backed correction jobs (one active per project)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, CorrectionJob] = {}
        self._project_active: Dict[str, str] = {}

    def get(self, job_id: str) -> Optional[CorrectionJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def active_for_project(self, project_id: str) -> Optional[CorrectionJob]:
        with self._lock:
            jid = self._project_active.get(project_id)
            return self._jobs.get(jid) if jid else None

    def cancel(self, job_id: str) -> Optional[CorrectionJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            job.cancel_requested = True
            if job.status == "queued":
                job.status = "cancelled"
                job.finished_at = time.time()
            # Unlock project immediately so another correction can start.
            if self._project_active.get(job.project_id) == job.id:
                self._project_active.pop(job.project_id, None)
            return job

    def start_background(
        self,
        *,
        project_id: str,
        workspace: Path,
        compare_fn: CompareFn,
        config: Optional[CorrectionConfig] = None,
        meta: Optional[Dict[str, Any]] = None,
        persist_dir: Optional[Path] = None,
        plan_fn: Optional[PatchPlanFn] = None,
        apply_fn: Optional[Callable[[List[Dict[str, Any]], str], Dict[str, Any]]] = None,
        rollback_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
        on_event: Optional[EventFn] = None,
    ) -> CorrectionJob:
        with self._lock:
            existing_id = self._project_active.get(project_id)
            if existing_id:
                existing = self._jobs.get(existing_id)
                if existing and existing.status in {"queued", "running"} and not existing.cancel_requested:
                    raise RuntimeError("correction already running for this project")
                self._project_active.pop(project_id, None)
            job = CorrectionJob(
                id=uuid.uuid4().hex[:12],
                project_id=project_id,
                config=config or CorrectionConfig(),
                meta=meta or {},
            )
            self._jobs[job.id] = job
            self._project_active[project_id] = job.id

        def _worker() -> None:
            def _forward(ev: Dict[str, Any]) -> None:
                if on_event:
                    try:
                        on_event(ev)
                    except Exception:  # noqa: BLE001
                        pass

            loop = CorrectionLoop(
                workspace,
                compare_fn=compare_fn,
                plan_fn=plan_fn,
                apply_fn=apply_fn,
                rollback_fn=rollback_fn,
                on_event=_forward,
                config=job.config,
            )
            try:
                loop.run(job)
            finally:
                if persist_dir:
                    _persist_job(persist_dir, job)
                with self._lock:
                    if self._project_active.get(project_id) == job.id:
                        self._project_active.pop(project_id, None)

        threading.Thread(target=_worker, name=f"correction-{job.id}", daemon=True).start()
        return job


def _persist_job(persist_dir: Path, job: CorrectionJob) -> None:
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    path = persist_dir / f"{job.id}.json"
    path.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


correction_manager = CorrectionManager()
