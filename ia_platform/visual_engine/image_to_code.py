"""Mockup → code → compare → agent retry (image-to-code correction strategy).

Builds agent goals from a mockup path + visual comparison reports, and runs
CodingAgent steps that the correction loop can apply / roll back.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from local_agent.checkpoint import RunCheckpoint


def summarize_visual_diff(report: Dict[str, Any], *, max_items: int = 8) -> str:
    """Compact, agent-readable summary of a visual comparison report."""
    if not isinstance(report, dict):
        return "Sem relatório visual."

    lines: List[str] = []
    sim = report.get("similarity")
    if isinstance(sim, (int, float)):
        lines.append(f"Similaridade atual: {float(sim) * 100:.1f}%")
    status = report.get("status")
    if status:
        lines.append(f"Status da comparação: {status}")

    layout = report.get("layoutChanges") or report.get("layout_changes") or []
    if isinstance(report.get("layoutDiff"), dict):
        layout = layout or report["layoutDiff"].get("layoutChanges") or []
    for change in layout[:max_items]:
        if not isinstance(change, dict):
            continue
        sel = str(change.get("selector") or "").strip() or "?"
        delta = change.get("delta") if isinstance(change.get("delta"), dict) else {}
        lines.append(
            "Layout "
            f"{sel}: Δw={int(delta.get('width') or 0)} "
            f"Δh={int(delta.get('height') or 0)} "
            f"Δx={int(delta.get('x') or 0)} "
            f"Δy={int(delta.get('y') or 0)}"
        )

    for region in (report.get("regions") or [])[:max_items]:
        if not isinstance(region, dict):
            continue
        el = region.get("probableElement") or region.get("probable_element") or {}
        if not isinstance(el, dict):
            continue
        sel = str(el.get("selector") or "").strip()
        if not sel:
            continue
        conf = el.get("confidence") or "?"
        cat = region.get("category") or "diff"
        lines.append(f"Região {cat} em {sel} (confiança {conf})")

    recs = report.get("recommendations") or []
    for rec in recs[:4]:
        text = str(rec).strip()
        if text:
            lines.append(f"Recomendação: {text}")

    if len(lines) <= 1:
        lines.append(
            "Diferenças estruturais detectadas — reescreva HTML/CSS para "
            "aproximar tipografia, espaçamento, cores e hierarquia do mockup."
        )
    return "\n".join(lines)


def build_bootstrap_goal(mockup: str, *, stack_hint: str = "html") -> str:
    """First-pass goal: implement UI from mockup image path in the workspace."""
    mockup = str(mockup or "").strip() or "mockups/reference.png"
    stack = (stack_hint or "html").strip().lower()
    if stack in {"react", "vite", "spa"}:
        stack_line = (
            "Implemente com React + Vite (ou a stack já presente no projeto). "
            "Mantenha componentes claros e estilos fiéis."
        )
    else:
        stack_line = (
            "Implemente com HTML/CSS/JS modernos (index.html + CSS). "
            "Se o projeto já tiver React/Vite, continue nessa stack."
        )
    return (
        "IMAGE-TO-CODE / MOCKUP → FRONTEND\n"
        f"Referência visual (mockup no workspace): {mockup}\n\n"
        "Objetivo: transformar esse mockup em código frontend pixel-fiel.\n"
        f"{stack_line}\n\n"
        "Regras:\n"
        "1) Replique layout, tipografia, cores, espaçamentos e hierarquia do mockup.\n"
        "2) Priorize fidelidade visual sobre features extras.\n"
        "3) Crie/atualize os arquivos necessários para o preview funcionar.\n"
        "4) Não invente seções que não existam no mockup.\n"
        "5) Ao terminar, o preview deve ficar o mais próximo possível da imagem.\n"
    )


def build_correction_goal(
    mockup: str,
    report: Dict[str, Any],
    *,
    attempt: int = 1,
    target_similarity: float = 0.95,
) -> str:
    """Follow-up goal: fix UI using visual diff feedback until target is reached."""
    mockup = str(mockup or "").strip() or "mockups/reference.png"
    target_pct = f"{float(target_similarity) * 100:.0f}%"
    diff = summarize_visual_diff(report)
    sim = report.get("similarity")
    sim_line = (
        f"Similaridade atual: {float(sim) * 100:.1f}% (meta: {target_pct})."
        if isinstance(sim, (int, float))
        else f"Meta de similaridade: {target_pct}."
    )
    return (
        "CORREÇÃO VISUAL ORIENTADA POR MOCKUP (tentativa "
        f"{max(1, int(attempt))})\n"
        f"Mockup de referência: {mockup}\n"
        f"{sim_line}\n\n"
        "Feedback do Visual Engine:\n"
        f"{diff}\n\n"
        "Tarefa:\n"
        "1) Edite o frontend para reduzir as diferenças acima.\n"
        "2) Foque nos seletores/regiões apontados (layout, tipografia, cores, espaçamento).\n"
        "3) Não remova o que já estiver correto; ajuste o que diverge do mockup.\n"
        "4) Mantenha o app funcional no preview.\n"
        f"5) Continue até aproximar ou superar {target_pct} de similaridade visual.\n"
    )


def needs_bootstrap(report: Optional[Dict[str, Any]], *, threshold: float = 0.45) -> bool:
    """True when the UI is missing/far from the mockup and should be (re)implemented."""
    if not isinstance(report, dict):
        return True
    sim = report.get("similarity")
    if not isinstance(sim, (int, float)):
        return True
    return float(sim) < float(threshold)


def make_agent_strategy_fns(
    workspace: Path,
    *,
    mockup: str,
    strategy: str = "agent",
    target_similarity: float = 0.95,
    max_agent_steps: int = 12,
    stack_hint: str = "html",
    cancel_check: Optional[Callable[[], bool]] = None,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Callable[..., Any]]:
    """Build plan/apply/rollback callables for CorrectionLoop agent/hybrid modes."""
    workspace = Path(workspace).resolve()
    strategy = (strategy or "agent").strip().lower()
    if strategy not in {"agent", "hybrid", "css"}:
        strategy = "agent"

    checkpoint_to_agent_run: Dict[str, str] = {}
    attempt_counter = {"n": 0}

    def _emit(typ: str, **payload: Any) -> None:
        if on_event:
            try:
                on_event({"type": typ, **payload})
            except Exception:  # noqa: BLE001
                pass

    def plan_fn(report: Dict[str, Any]) -> List[Dict[str, Any]]:
        attempt_counter["n"] += 1
        attempt = attempt_counter["n"]
        report = report if isinstance(report, dict) else {}

        if strategy == "css":
            from .patches import plan_heuristic_patches

            return plan_heuristic_patches(report)

        if strategy == "hybrid" and not needs_bootstrap(report):
            from .patches import plan_heuristic_patches

            css_patches = plan_heuristic_patches(report)
            if css_patches:
                return css_patches

        if needs_bootstrap(report):
            goal = build_bootstrap_goal(mockup, stack_hint=stack_hint)
            mode = "bootstrap"
        else:
            goal = build_correction_goal(
                mockup,
                report,
                attempt=attempt,
                target_similarity=target_similarity,
            )
            mode = "refine"
        return [
            {
                "kind": "agent",
                "mode": mode,
                "goal": goal,
                "attempt": attempt,
                "mockup": mockup,
            }
        ]

    def apply_fn(patches: List[Dict[str, Any]], run_id: str) -> Dict[str, Any]:
        if not patches:
            return {"ok": False, "written": [], "error": "no patches"}

        if patches[0].get("kind") != "agent":
            from .patches import apply_patches

            return apply_patches(workspace, patches, run_id=run_id)

        goal = str(patches[0].get("goal") or "").strip()
        mode = str(patches[0].get("mode") or "refine")
        if not goal:
            return {"ok": False, "written": [], "error": "empty agent goal"}

        _emit("correction.agent_starting", mode=mode, checkpoint_id=run_id)
        result = run_agent_step(
            workspace,
            goal,
            max_steps=max_agent_steps,
            cancel_check=cancel_check,
            preferred_run_id=run_id,
        )
        agent_run_id = str(result.get("run_id") or run_id)
        checkpoint_to_agent_run[run_id] = agent_run_id
        _emit(
            "correction.agent_finished",
            mode=mode,
            checkpoint_id=run_id,
            agent_run_id=agent_run_id,
            status=result.get("status"),
            created=len(result.get("created_files") or []),
            modified=len(result.get("modified_files") or []),
        )
        written = list(result.get("created_files") or []) + list(result.get("modified_files") or [])
        return {
            "ok": bool(result.get("ok", True)),
            "written": written,
            "patches": 1,
            "kind": "agent",
            "mode": mode,
            "run_id": agent_run_id,
            "status": result.get("status"),
            "summary": result.get("summary"),
            "error": result.get("error"),
        }

    def rollback_fn(run_id: str) -> Dict[str, Any]:
        agent_run_id = checkpoint_to_agent_run.get(run_id) or run_id
        cp = RunCheckpoint.load(workspace, agent_run_id)
        if cp is not None:
            restored = cp.restore()
            restored["kind"] = "agent"
            return restored
        from .patches import rollback_patches

        return rollback_patches(workspace, run_id)

    return {"plan_fn": plan_fn, "apply_fn": apply_fn, "rollback_fn": rollback_fn}


def run_agent_step(
    workspace: Path,
    goal: str,
    *,
    max_steps: int = 12,
    cancel_check: Optional[Callable[[], bool]] = None,
    preferred_run_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one CodingAgent pass under the workspace run lock."""
    from ia_platform.run_manager import run_manager
    from local_agent.agent import CodingAgent
    from local_agent.config import AgentConfig

    workspace = Path(workspace).resolve()
    run_id = run_manager.acquire(str(workspace))
    if not run_id:
        return {
            "ok": False,
            "error": "workspace busy (another agent run is active)",
            "run_id": preferred_run_id,
            "created_files": [],
            "modified_files": [],
        }

    # Prefer correction checkpoint id for rollback mapping when free.
    agent_run_id = preferred_run_id or run_id
    try:
        run_manager.set_goal(run_id, goal[:240])
    except Exception:  # noqa: BLE001
        pass

    def _cancelled() -> bool:
        if cancel_check and cancel_check():
            return True
        return run_manager.is_cancelled(run_id)

    try:
        cfg = AgentConfig.from_args(
            workspace,
            model=model,
            max_steps=max(4, int(max_steps or 12)),
            verbose=True,
            no_git=True,
        )
        # Keep agent checkpoint keyed by preferred id when possible.
        cfg.run_id = agent_run_id
        cfg.cancel_check = _cancelled
        report = CodingAgent(cfg).run(goal)
        status = getattr(getattr(report, "status", None), "value", None) or str(
            getattr(report, "status", "") or ""
        )
        return {
            "ok": True,
            "run_id": agent_run_id,
            "lock_run_id": run_id,
            "status": status,
            "summary": str(getattr(report, "summary", "") or "")[:500],
            "created_files": list(getattr(report, "created_files", []) or []),
            "modified_files": list(getattr(report, "modified_files", []) or []),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(exc),
            "run_id": agent_run_id,
            "lock_run_id": run_id,
            "created_files": [],
            "modified_files": [],
        }
    finally:
        run_manager.clear(run_id)
