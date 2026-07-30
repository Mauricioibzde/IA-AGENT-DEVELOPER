"""Mockup → code → compare → agent retry (image-to-code correction strategy).

Builds agent goals from a mockup path + visual comparison reports, and runs
CodingAgent steps that the correction loop can apply / roll back.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from local_agent.checkpoint import RunCheckpoint

CONF_RANK = {"high": 0, "medium": 1, "low": 2}
BOOTSTRAP_SIMILARITY = 0.62
HYBRID_CSS_MIN_SIMILARITY = 0.82


def detect_stack_hint(workspace: Path) -> str:
    """Infer a practical stack hint from workspace files."""
    root = Path(workspace)
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            text = pkg.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            text = ""
        if "react" in text or "vite" in text or "next" in text:
            return "react"
    if (root / "src" / "App.tsx").is_file() or (root / "src" / "App.jsx").is_file():
        return "react"
    if (root / "index.html").is_file():
        return "html"
    return "html"


def list_workspace_files(workspace: Path, *, limit: int = 24) -> List[str]:
    """Small inventory of frontend-ish files for agent context."""
    root = Path(workspace).resolve()
    interesting = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".svg"}
    skip_dirs = {".git", "node_modules", ".agent", "dist", "build", "__pycache__", "artifacts"}
    found: List[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in skip_dirs for part in rel_parts):
            continue
        if path.suffix.lower() not in interesting and path.name not in {"package.json", "README.md"}:
            continue
        found.append(str(path.relative_to(root)).replace("\\", "/"))
        if len(found) >= limit:
            break
    return found


def _workspace_rel(workspace: Optional[Path], path_str: str) -> str:
    raw = str(path_str or "").strip()
    if not raw:
        return ""
    if workspace is None:
        return raw.replace("\\", "/")
    try:
        return str(Path(raw).resolve().relative_to(Path(workspace).resolve())).replace("\\", "/")
    except (ValueError, OSError):
        return raw.replace("\\", "/")


def _artifact_paths(report: Dict[str, Any], *, workspace: Optional[Path] = None) -> List[str]:
    arts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    out: List[str] = []
    for key in (
        "diff",
        "diffImage",
        "actual",
        "actualNormalized",
        "current",
        "reference",
        "referenceNormalized",
        "overlay",
    ):
        val = arts.get(key)
        if isinstance(val, str) and val.strip():
            out.append(f"{key}: {_workspace_rel(workspace, val.strip())}")
        elif isinstance(val, dict):
            path = val.get("path") or val.get("url") or val.get("file")
            if path:
                out.append(f"{key}: {_workspace_rel(workspace, str(path))}")
    return out[:8]


def pick_report_image(report: Dict[str, Any], *keys: str) -> Optional[str]:
    """Return the first existing filesystem path among artifact keys."""
    arts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    for key in keys:
        val = arts.get(key)
        path_str = ""
        if isinstance(val, str):
            path_str = val.strip()
        elif isinstance(val, dict):
            path_str = str(val.get("path") or val.get("file") or "").strip()
        if path_str and Path(path_str).is_file():
            return path_str
    return None


def _sorted_regions(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    regions = [r for r in (report.get("regions") or []) if isinstance(r, dict)]

    def key(region: Dict[str, Any]) -> tuple:
        el = region.get("probableElement") or region.get("probable_element") or {}
        conf = str((el or {}).get("confidence") or "low").lower()
        return (CONF_RANK.get(conf, 9), str(region.get("category") or ""))

    return sorted(regions, key=key)


def summarize_visual_diff(
    report: Dict[str, Any],
    *,
    max_items: int = 10,
    workspace: Optional[Path] = None,
) -> str:
    """Compact, agent-readable summary of a visual comparison report."""
    if not isinstance(report, dict):
        return "Sem relatório visual."

    lines: List[str] = []
    sim = report.get("similarity")
    if isinstance(sim, (int, float)):
        lines.append(f"Similaridade atual: {float(sim) * 100:.1f}%")
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    diff_pct = summary.get("diffPercent")
    if isinstance(diff_pct, (int, float)):
        lines.append(f"Pixels diferentes: {float(diff_pct) * 100:.2f}%")
    status = report.get("status")
    if status:
        lines.append(f"Status da comparação: {status}")
    cid = report.get("comparisonId") or report.get("comparison_id")
    if cid:
        lines.append(f"comparisonId: {cid}")

    arts = _artifact_paths(report, workspace=workspace)
    for art in arts:
        lines.append(f"Artefato {art}")
    if arts:
        lines.append(
            "Abra os artefatos diff/actual no workspace (caminhos acima) e corrija "
            "o que divergir visualmente — não invente."
        )

    layout = report.get("layoutChanges") or report.get("layout_changes") or []
    if isinstance(report.get("layoutDiff"), dict):
        layout = layout or report["layoutDiff"].get("layoutChanges") or []
    scored_layout: List[tuple] = []
    for change in layout:
        if not isinstance(change, dict):
            continue
        delta = change.get("delta") if isinstance(change.get("delta"), dict) else {}
        magnitude = sum(abs(int(delta.get(k) or 0)) for k in ("width", "height", "x", "y"))
        scored_layout.append((magnitude, change))
    scored_layout.sort(key=lambda item: item[0], reverse=True)
    for _, change in scored_layout[:max_items]:
        sel = str(change.get("selector") or "").strip() or "?"
        delta = change.get("delta") if isinstance(change.get("delta"), dict) else {}
        lines.append(
            "Layout "
            f"{sel}: Δw={int(delta.get('width') or 0)} "
            f"Δh={int(delta.get('height') or 0)} "
            f"Δx={int(delta.get('x') or 0)} "
            f"Δy={int(delta.get('y') or 0)}"
        )

    style_changes = report.get("styleChanges") or report.get("style_changes") or []
    for change in style_changes[:max_items]:
        if not isinstance(change, dict):
            continue
        sel = str(change.get("selector") or "").strip() or "?"
        prop = str(change.get("property") or change.get("prop") or "").strip()
        before = change.get("before") or change.get("expected") or change.get("reference")
        after = change.get("after") or change.get("actual") or change.get("current")
        if prop:
            lines.append(f"Estilo {sel}: {prop} {before!s} → {after!s}")
        else:
            lines.append(f"Estilo {sel}: {change}")

    for region in _sorted_regions(report)[:max_items]:
        el = region.get("probableElement") or region.get("probable_element") or {}
        if not isinstance(el, dict):
            continue
        sel = str(el.get("selector") or "").strip()
        if not sel:
            continue
        conf = el.get("confidence") or "?"
        cat = region.get("category") or "diff"
        rect = el.get("rect") or region.get("bbox") or region.get("rect") or {}
        where = ""
        if isinstance(rect, dict) and any(k in rect for k in ("x", "y", "width", "height", "w", "h")):
            x = int(rect.get("x") or 0)
            y = int(rect.get("y") or 0)
            w = int(rect.get("width") or rect.get("w") or 0)
            h = int(rect.get("height") or rect.get("h") or 0)
            where = f" @({x},{y},{w}x{h})"
        text = str(el.get("text") or region.get("text") or "").strip()
        text_bit = f' texto="{text[:48]}"' if text else ""
        sev = region.get("severity") or region.get("score") or ""
        sev_bit = f" sev={sev}" if sev != "" else ""
        lines.append(f"Região prioritária [{cat}/{conf}]{sev_bit} → {sel}{where}{text_bit}")

    recs = report.get("recommendations") or []
    for rec in recs[:5]:
        text = str(rec).strip()
        if text:
            lines.append(f"Recomendação: {text}")

    for warning in (report.get("warnings") or [])[:3]:
        text = str(warning).strip()
        if text:
            lines.append(f"Aviso: {text}")

    if len(lines) <= 2:
        lines.append(
            "Diferenças estruturais detectadas — reescreva HTML/CSS para "
            "aproximar tipografia, espaçamento, cores e hierarquia do mockup."
        )
    return "\n".join(lines)


def build_priority_checklist(report: Dict[str, Any], *, limit: int = 6) -> List[str]:
    """Actionable checklist derived from visual diffs."""
    items: List[str] = []
    for region in _sorted_regions(report):
        el = region.get("probableElement") or region.get("probable_element") or {}
        if not isinstance(el, dict):
            continue
        sel = str(el.get("selector") or "").strip()
        if not sel:
            continue
        cat = str(region.get("category") or "layout")
        rect = el.get("rect") or region.get("bbox") or region.get("rect") or {}
        loc = ""
        if isinstance(rect, dict) and any(k in rect for k in ("x", "y", "width", "height", "w", "h")):
            x = int(rect.get("x") or 0)
            y = int(rect.get("y") or 0)
            w = int(rect.get("width") or rect.get("w") or 0)
            h = int(rect.get("height") or rect.get("h") or 0)
            loc = f" em ({x},{y},{w}x{h})"
        text = str(el.get("text") or region.get("text") or "").strip()
        text_bit = f' (“{text[:40]}”)' if text else ""
        if cat in {"typography", "text"}:
            items.append(f"Ajustar tipografia/cor/peso em `{sel}`{loc}{text_bit}")
        elif cat in {"spacing", "layout"}:
            items.append(f"Corrigir espaçamento/posição/tamanho de `{sel}`{loc}")
        elif cat in {"color", "background"}:
            items.append(f"Alinhar cores/fundo de `{sel}`{loc} ao mockup")
        else:
            items.append(f"Aproximar `{sel}`{loc} do mockup ({cat}){text_bit}")
        if len(items) >= limit:
            break

    style_changes = report.get("styleChanges") or report.get("style_changes") or []
    for change in style_changes:
        if len(items) >= limit:
            break
        if not isinstance(change, dict):
            continue
        sel = str(change.get("selector") or "").strip()
        prop = str(change.get("property") or change.get("prop") or "").strip()
        if not sel or not prop:
            continue
        before = change.get("before") or change.get("expected") or change.get("reference")
        after = change.get("after") or change.get("actual") or change.get("current")
        items.append(f"Corrigir `{sel}` {prop}: {after!s} → {before!s} (alvo mockup)")

    layout = report.get("layoutChanges") or []
    if isinstance(report.get("layoutDiff"), dict):
        layout = layout or report["layoutDiff"].get("layoutChanges") or []
    for change in layout:
        if len(items) >= limit:
            break
        if not isinstance(change, dict):
            continue
        sel = str(change.get("selector") or "").strip()
        if not sel:
            continue
        items.append(f"Recalibrar geometria de `{sel}` (width/height/posição)")
    if not items:
        items.append("Revisar hierarquia visual completa contra o mockup (header, conteúdo, botões, espaçamento)")
    # de-dupe preserve order
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_bootstrap_goal(
    mockup: str,
    *,
    stack_hint: str = "html",
    workspace_files: Optional[Sequence[str]] = None,
    vision_spec: str = "",
    palette_block: str = "",
) -> str:
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
    files = list(workspace_files or [])
    files_block = ""
    if files:
        files_block = "Arquivos atuais do projeto:\n- " + "\n- ".join(files[:20]) + "\n\n"
    vision_block = ""
    if (vision_spec or "").strip():
        vision_block = (
            "Especificação visual (modelo de visão — trate como verdade do mockup):\n"
            f"{vision_spec.strip()[:4500]}\n\n"
        )
    palette = ""
    if (palette_block or "").strip():
        palette = f"{palette_block.strip()}\n\n"
    return (
        "IMAGE-TO-CODE / MOCKUP → FRONTEND\n"
        f"Referência visual (arquivo): {mockup}\n\n"
        "Objetivo: transformar esse mockup em código frontend o mais pixel-fiel possível.\n"
        f"{stack_line}\n\n"
        f"{palette}"
        f"{vision_block}"
        f"{files_block}"
        "Regras:\n"
        "1) Replique layout, tipografia, cores, espaçamentos, raios e hierarquia do mockup.\n"
        "2) Priorize fidelidade visual sobre features extras.\n"
        "3) Crie/atualize os arquivos necessários para o preview funcionar de imediato.\n"
        "4) Não invente seções que não existam no mockup / na especificação visual.\n"
        "5) Prefira CSS limpo e estrutura semântica; evite placeholders genéricos.\n"
        "6) Ao terminar, o preview deve ficar visualmente próximo da imagem de referência.\n"
    )


def build_correction_goal(
    mockup: str,
    report: Dict[str, Any],
    *,
    attempt: int = 1,
    target_similarity: float = 0.95,
    workspace_files: Optional[Sequence[str]] = None,
    vision_spec: str = "",
    vision_diff: str = "",
    palette_block: str = "",
    workspace: Optional[Path] = None,
) -> str:
    """Follow-up goal: fix UI using visual diff feedback until target is reached."""
    mockup = str(mockup or "").strip() or "mockups/reference.png"
    target_pct = f"{float(target_similarity) * 100:.0f}%"
    diff = summarize_visual_diff(report, workspace=workspace)
    checklist = build_priority_checklist(report)
    sim = report.get("similarity")
    sim_line = (
        f"Similaridade atual: {float(sim) * 100:.1f}% (meta: {target_pct})."
        if isinstance(sim, (int, float))
        else f"Meta de similaridade: {target_pct}."
    )
    files = list(workspace_files or [])
    files_block = ""
    if files:
        files_block = "Arquivos relevantes:\n- " + "\n- ".join(files[:16]) + "\n\n"
    checklist_block = "\n".join(f"- {item}" for item in checklist)
    vision_block = ""
    if (vision_spec or "").strip():
        vision_block = (
            "Lembrete da especificação visual (visão):\n"
            f"{vision_spec.strip()[:2200]}\n\n"
        )
    diff_vision_block = ""
    if (vision_diff or "").strip():
        diff_vision_block = f"{vision_diff.strip()[:3200]}\n\n"
    palette = ""
    if (palette_block or "").strip():
        palette = f"{palette_block.strip()}\n\n"
    return (
        "CORREÇÃO VISUAL ORIENTADA POR MOCKUP (tentativa "
        f"{max(1, int(attempt))})\n"
        f"Mockup de referência: {mockup}\n"
        f"{sim_line}\n\n"
        f"{palette}"
        f"{diff_vision_block}"
        f"{vision_block}"
        f"{files_block}"
        "Feedback do Visual Engine:\n"
        f"{diff}\n\n"
        "Checklist prioritário:\n"
        f"{checklist_block}\n\n"
        "Tarefa:\n"
        "1) Edite o frontend para reduzir as diferenças acima (comece pelo diagnóstico visual + checklist).\n"
        "2) Use a especificação visual + diffs juntos (não ignore nenhum dos dois).\n"
        "3) Foque nos seletores/regiões de maior confiança e nas cores da paleta amostrada.\n"
        "4) Não remova o que já estiver correto; ajuste só o que diverge do mockup.\n"
        "5) Mantenha o app funcional no preview.\n"
        f"6) Continue até aproximar ou superar {target_pct} de similaridade visual.\n"
    )


def needs_bootstrap(report: Optional[Dict[str, Any]], *, threshold: float = BOOTSTRAP_SIMILARITY) -> bool:
    """True when the UI is missing/far from the mockup and should be (re)implemented."""
    if not isinstance(report, dict):
        return True
    sim = report.get("similarity")
    if not isinstance(sim, (int, float)):
        return True
    return float(sim) < float(threshold)


def wait_for_preview_settle(
    *,
    seconds: float = 1.6,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> None:
    """Pause briefly so preview/static files settle before re-compare."""
    deadline = time.time() + max(0.0, float(seconds))
    while time.time() < deadline:
        if cancel_check and cancel_check():
            return
        time.sleep(0.15)


def make_agent_strategy_fns(
    workspace: Path,
    *,
    mockup: str,
    strategy: str = "agent",
    target_similarity: float = 0.95,
    max_agent_steps: int = 12,
    stack_hint: str = "",
    settle_seconds: float = 1.6,
    use_vision: bool = True,
    vision_model: Optional[str] = None,
    ollama_host: str = "http://127.0.0.1:11434",
    cancel_check: Optional[Callable[[], bool]] = None,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Callable[..., Any]]:
    """Build plan/apply/rollback callables for CorrectionLoop agent/hybrid modes."""
    workspace = Path(workspace).resolve()
    strategy = (strategy or "agent").strip().lower()
    if strategy not in {"agent", "hybrid", "css"}:
        strategy = "agent"
    resolved_stack = (stack_hint or "").strip() or detect_stack_hint(workspace)

    checkpoint_to_agent_run: Dict[str, str] = {}
    attempt_counter = {"n": 0}
    last_mode = {"value": ""}
    vision_cache: Dict[str, Any] = {
        "spec": "",
        "structured": {},
        "tried": False,
        "model": None,
        "error": None,
        "runs": 0,
        "diff_spec": "",
        "diff_for": None,
        "palette": "",
        "palette_tried": False,
    }

    def _emit(typ: str, **payload: Any) -> None:
        if on_event:
            try:
                on_event({"type": typ, **payload})
            except Exception:  # noqa: BLE001
                pass

    def _ensure_palette() -> str:
        if vision_cache["palette_tried"]:
            return str(vision_cache.get("palette") or "")
        vision_cache["palette_tried"] = True
        try:
            from .palette import format_palette_for_goal, resolve_mockup_path, sample_palette

            path = resolve_mockup_path(workspace, mockup)
            if not path:
                return ""
            result = sample_palette(path)
            if result.get("ok") and result.get("colors"):
                block = format_palette_for_goal(list(result["colors"]))
                vision_cache["palette"] = block
                _emit(
                    "vision.palette",
                    colors=len(result["colors"]),
                    preview=block[:400],
                )
            else:
                _emit("vision.palette_skipped", reason=str(result.get("error") or "empty"))
        except Exception as exc:  # noqa: BLE001
            _emit("vision.palette_skipped", reason=str(exc))
        return str(vision_cache.get("palette") or "")

    def _ensure_vision_spec(*, force: bool = False) -> str:
        if not use_vision:
            return ""
        if vision_cache["tried"] and not force:
            return str(vision_cache.get("spec") or "")
        vision_cache["tried"] = True
        vision_cache["runs"] = int(vision_cache.get("runs") or 0) + 1
        try:
            from .vision import describe_mockup

            result = describe_mockup(
                workspace,
                mockup,
                host=ollama_host,
                model=vision_model,
                use_cache=not force,
                cancel_check=cancel_check,
                on_event=on_event,
            )
            if result.get("ok") and result.get("spec"):
                vision_cache["spec"] = str(result["spec"])
                vision_cache["structured"] = result.get("structured") or {}
                vision_cache["model"] = result.get("model")
                vision_cache["error"] = None
            else:
                vision_cache["error"] = result.get("error")
                _emit(
                    "vision.skipped",
                    reason=str(result.get("error") or "unavailable"),
                    model=result.get("model"),
                )
        except Exception as exc:  # noqa: BLE001
            vision_cache["error"] = str(exc)
            _emit("vision.skipped", reason=str(exc))
        return str(vision_cache.get("spec") or "")

    def _should_refresh_vision(report: Dict[str, Any], attempt: int) -> bool:
        if not use_vision or not vision_cache.get("tried"):
            return False
        sim = report.get("similarity")
        if not isinstance(sim, (int, float)):
            return False
        if float(sim) >= 0.78:
            return False
        return attempt in {3, 5} and int(vision_cache.get("runs") or 0) < 3

    def _ensure_vision_diff(report: Dict[str, Any], *, attempt: int) -> str:
        """Compare mockup × actual screenshot with vision when refining."""
        if not use_vision:
            return ""
        sim = report.get("similarity")
        sim_f = float(sim) if isinstance(sim, (int, float)) else 0.0
        # Skip when already very close or still empty bootstrap territory without actual.
        if sim_f >= 0.93:
            return str(vision_cache.get("diff_spec") or "")
        cid = str(report.get("comparisonId") or report.get("comparison_id") or "") or f"attempt-{attempt}"
        if vision_cache.get("diff_for") == cid and vision_cache.get("diff_spec"):
            return str(vision_cache.get("diff_spec") or "")

        actual = pick_report_image(report, "actualNormalized", "actual", "current")
        if not actual:
            return ""
        # Prefer running on refine attempts (2+) or mid-fidelity first pass.
        if attempt < 2 and sim_f < 0.35:
            return ""

        diff = pick_report_image(report, "diff", "diffImage")
        try:
            from .vision import compare_mockup_vs_actual

            result = compare_mockup_vs_actual(
                workspace,
                mockup,
                actual,
                diff_path=diff,
                host=ollama_host,
                model=vision_model,
                cancel_check=cancel_check,
                on_event=on_event,
            )
            vision_cache["diff_for"] = cid
            if result.get("ok") and result.get("spec"):
                vision_cache["diff_spec"] = str(result["spec"])
                if result.get("model"):
                    vision_cache["model"] = result.get("model")
            else:
                _emit(
                    "vision.diff_skipped",
                    reason=str(result.get("error") or "unavailable"),
                    comparison_id=cid,
                )
        except Exception as exc:  # noqa: BLE001
            _emit("vision.diff_skipped", reason=str(exc), comparison_id=cid)
        return str(vision_cache.get("diff_spec") or "")

    def plan_fn(report: Dict[str, Any]) -> List[Dict[str, Any]]:
        attempt_counter["n"] += 1
        attempt = attempt_counter["n"]
        report = report if isinstance(report, dict) else {}
        files = list_workspace_files(workspace)
        palette_block = _ensure_palette()
        force_vision = _should_refresh_vision(report, attempt)
        if force_vision:
            _emit("vision.refresh", attempt=attempt, similarity=report.get("similarity"))
        vision_spec = (
            _ensure_vision_spec(force=force_vision) if strategy in {"agent", "hybrid"} else ""
        )

        if strategy == "css":
            from .patches import plan_heuristic_patches

            return plan_heuristic_patches(report)

        # Hybrid: only apply measurable CSS when already close; otherwise agent.
        use_css = False
        sim = report.get("similarity")
        sim_f = float(sim) if isinstance(sim, (int, float)) else 0.0
        if (
            strategy == "hybrid"
            and not needs_bootstrap(report)
            and sim_f >= HYBRID_CSS_MIN_SIMILARITY
            and attempt % 2 == 0
        ):
            from .patches import plan_heuristic_patches

            css_patches = plan_heuristic_patches(
                report,
                allow_marker=False,
                meaningful_only=True,
            )
            if css_patches:
                use_css = True
                last_mode["value"] = "css"
                return css_patches

        if needs_bootstrap(report) or (strategy == "hybrid" and not use_css and attempt == 1 and sim_f < 0.75):
            goal = build_bootstrap_goal(
                mockup,
                stack_hint=resolved_stack,
                workspace_files=files,
                vision_spec=vision_spec,
                palette_block=palette_block,
            )
            mode = "bootstrap"
            vision_diff = ""
        else:
            vision_diff = _ensure_vision_diff(report, attempt=attempt) if strategy in {"agent", "hybrid"} else ""
            goal = build_correction_goal(
                mockup,
                report,
                attempt=attempt,
                target_similarity=target_similarity,
                workspace_files=files,
                vision_spec=vision_spec,
                vision_diff=vision_diff,
                palette_block=palette_block,
                workspace=workspace,
            )
            mode = "refine"
        last_mode["value"] = mode
        return [
            {
                "kind": "agent",
                "mode": mode,
                "goal": goal,
                "attempt": attempt,
                "mockup": mockup,
                "stack": resolved_stack,
                "vision_model": vision_cache.get("model"),
                "has_vision_spec": bool(vision_spec),
                "has_vision_diff": bool(vision_diff) if mode == "refine" else False,
                "has_palette": bool(palette_block),
            }
        ]

    def apply_fn(patches: List[Dict[str, Any]], run_id: str) -> Dict[str, Any]:
        if not patches:
            return {"ok": False, "written": [], "error": "no patches"}

        if patches[0].get("kind") != "agent":
            from .patches import apply_patches

            applied = apply_patches(workspace, patches, run_id=run_id)
            wait_for_preview_settle(seconds=min(1.0, settle_seconds), cancel_check=cancel_check)
            return applied

        goal = str(patches[0].get("goal") or "").strip()
        mode = str(patches[0].get("mode") or "refine")
        if not goal:
            return {"ok": False, "written": [], "error": "empty agent goal"}

        _emit("correction.agent_starting", mode=mode, checkpoint_id=run_id, attempt=patches[0].get("attempt"))
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
            summary=(result.get("summary") or "")[:180],
        )
        # Let static/dev preview pick up file writes before the next compare.
        wait_for_preview_settle(seconds=settle_seconds, cancel_check=cancel_check)
        _emit("correction.preview_settled", checkpoint_id=run_id, seconds=settle_seconds)
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
            wait_for_preview_settle(seconds=min(1.0, settle_seconds), cancel_check=cancel_check)
            return restored
        from .patches import rollback_patches

        restored = rollback_patches(workspace, run_id)
        wait_for_preview_settle(seconds=min(1.0, settle_seconds), cancel_check=cancel_check)
        return restored

    return {
        "plan_fn": plan_fn,
        "apply_fn": apply_fn,
        "rollback_fn": rollback_fn,
        "vision_cache": vision_cache,
    }


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
