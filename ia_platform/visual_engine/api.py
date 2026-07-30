"""HTTP helpers for Visual Engine routes (used by PlatformHandler)."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .bridge import VisualEngineBridgeError
from .models import CompareRequest, Side
from .service import VisualEngine


def engine_for(project_dir: Path, project_id: str, forge_port: int = 8787) -> VisualEngine:
    return VisualEngine(project_dir, project_id=project_id, forge_port=forge_port)


def parse_side(raw: Any, *, default_type: str = "url") -> Side:
    if isinstance(raw, str):
        # Heuristic: paths ending in image ext → image
        lower = raw.lower()
        if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            return Side(type="image", value=raw)
        return Side(type="url", value=raw)  # type: ignore[arg-type]
    if not isinstance(raw, dict):
        raise ValueError("source/target must be object or string")
    stype = str(raw.get("type") or default_type)
    value = str(raw.get("value") or raw.get("url") or raw.get("path") or "")
    if not value:
        raise ValueError("side.value is required")
    if stype not in {"url", "image", "artifact"}:
        raise ValueError(f"unsupported side type: {stype}")
    return Side(type=stype, value=value)  # type: ignore[arg-type]


def handle_status(engine: VisualEngine) -> Tuple[int, Dict[str, Any]]:
    return 200, engine.status()


def handle_list(engine: VisualEngine) -> Tuple[int, Dict[str, Any]]:
    return 200, {"comparisons": engine.list_comparisons()}


def handle_get(engine: VisualEngine, comparison_id: str) -> Tuple[int, Dict[str, Any]]:
    item = engine.get_comparison(comparison_id)
    if not item:
        return 404, {"error": "comparison not found"}
    return 200, {"comparison": item}


def handle_delete(engine: VisualEngine, comparison_id: str) -> Tuple[int, Dict[str, Any]]:
    try:
        removed = engine.delete_comparison(comparison_id)
    except ValueError as exc:
        return 400, {"error": str(exc)}
    if not removed and not engine.get_comparison(comparison_id):
        return 404, {"error": "comparison not found"}
    return 200, {"ok": True, "deleted": comparison_id}


def handle_capture(engine: VisualEngine, data: Dict[str, Any], *, host_header: str) -> Tuple[int, Dict[str, Any]]:
    try:
        viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else None
        options = data.get("options") if isinstance(data.get("options"), dict) else {}
        if data.get("preview") or data.get("use_preview") or not data.get("url"):
            report = engine.capture_preview(
                host_header=host_header,
                mode=str(data.get("mode") or "auto"),
                file_path=str(data.get("path") or "index.html"),
                viewport=viewport,
                **options,
            )
        else:
            report = engine.capture_url(str(data["url"]), viewport=viewport, **options)
        return 200, {"ok": True, "report": report.to_dict()}
    except FileNotFoundError as exc:
        return 404, {"error": str(exc)}
    except (ValueError, VisualEngineBridgeError) as exc:
        return 400, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": str(exc)}


def handle_compare(engine: VisualEngine, data: Dict[str, Any], *, host_header: str) -> Tuple[int, Dict[str, Any]]:
    try:
        # Convenience: compare preview against a mockup path
        if data.get("mockup") and not data.get("source"):
            data = {
                **data,
                "source": {"type": "image", "value": str(data["mockup"])},
                "target": data.get("target")
                or {
                    "type": "url",
                    "value": engine.resolve_preview_url(
                        host_header=host_header,
                        mode=str(data.get("mode") or "auto"),
                        file_path=str(data.get("path") or "index.html"),
                    ),
                },
            }
        # Convenience: url1/url2 legacy shape from puppeteer-compare
        if data.get("url1") and data.get("url2") and not data.get("source"):
            data = {
                **data,
                "source": {"type": "url", "value": str(data["url1"])},
                "target": {"type": "url", "value": str(data["url2"])},
            }
        # Compare current preview vs a second URL
        if data.get("preview_vs_url") and not data.get("source"):
            data = {
                **data,
                "source": {
                    "type": "url",
                    "value": engine.resolve_preview_url(
                        host_header=host_header,
                        mode=str(data.get("mode") or "auto"),
                        file_path=str(data.get("path") or "index.html"),
                    ),
                },
                "target": {"type": "url", "value": str(data["preview_vs_url"])},
            }

        source = parse_side(data.get("source"), default_type="url")
        target = parse_side(data.get("target"), default_type="url")
        viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else {"width": 1366, "height": 768}
        viewports = data.get("viewports")
        options = data.get("options") if isinstance(data.get("options"), dict) else {}
        pixel_perfect = bool(
            data.get("pixel_perfect")
            or data.get("pixelPerfect")
            or str(data.get("mode") or "").lower() in {"pixel_perfect", "pixel-perfect"}
            or data.get("suite")
        )
        if pixel_perfect or (isinstance(viewports, list) and len(viewports) > 1):
            return handle_pixel_perfect(
                engine,
                {
                    **data,
                    "source": {"type": source.type, "value": source.value},
                    "target": {"type": target.type, "value": target.value},
                    "options": options,
                },
            )

        report = engine.compare(
            CompareRequest(
                source=source,
                target=target,
                viewport=viewport,
                options=options,
                comparison_id=data.get("comparisonId") or data.get("testName"),
            )
        )
        return 200, {"ok": True, "report": report.to_dict()}
    except FileNotFoundError as exc:
        return 404, {"error": str(exc)}
    except (ValueError, VisualEngineBridgeError) as exc:
        return 400, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": str(exc)}


def handle_list_suites(_engine: VisualEngine) -> Tuple[int, Dict[str, Any]]:
    from .pixel_perfect import list_suites

    return 200, {"ok": True, "suites": list_suites()}


def handle_pixel_perfect(engine: VisualEngine, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Run Pixel Perfect multi-viewport suite and persist aggregate report."""
    from .pixel_perfect import (
        persist_suite_report,
        resolve_suite_viewports,
        run_pixel_perfect,
        ViewportResult,
        SuiteReport,
        aggregate_scores,
    )

    try:
        source = parse_side(data.get("source"), default_type="url")
        target = parse_side(data.get("target"), default_type="url")
        options = data.get("options") if isinstance(data.get("options"), dict) else {}
        target_sim = float(data.get("target_similarity") or data.get("targetSimilarity") or 0.95)
        suite = data.get("suite")
        viewports = data.get("viewports") if isinstance(data.get("viewports"), list) else None

        # Prefer single CLI process + browser pool (Phase 8).
        use_multi = data.get("use_multi", True)
        if use_multi and (source.type == "url" or target.type == "url"):
            suite_id, suite_name, resolved = resolve_suite_viewports(
                suite=str(suite) if suite else None,
                viewports=viewports,
            )
            reports = engine.compare_multi(
                source=source,
                target=target,
                viewports=resolved,
                options=options,
            )
            results = []
            for vp, report in zip(resolved, reports):
                sim = report.similarity
                results.append(
                    ViewportResult(
                        viewport=vp,
                        similarity=float(sim) if isinstance(sim, (int, float)) else None,
                        passed=isinstance(sim, (int, float)) and float(sim) >= target_sim,
                        target_similarity=target_sim,
                        comparison_id=report.comparison_id,
                        status=report.status,
                        report=report.to_dict(),
                    )
                )
            agg = aggregate_scores(results, target=target_sim)
            primary = ""
            for r in results:
                if not r.passed and r.comparison_id:
                    primary = r.comparison_id
                    break
            if not primary:
                for r in results:
                    if r.comparison_id:
                        primary = r.comparison_id
                        break
            suite_report = SuiteReport(
                suite_id=suite_id,
                suite_name=suite_name,
                status=str(agg["status"]),
                target_similarity=target_sim,
                viewports=results,
                min_similarity=agg["min"],
                avg_similarity=agg["avg"],
                max_similarity=agg["max"],
                passed_count=int(agg["passed"]),
                failed_count=int(agg["failed"]),
                worst_viewport_id=agg["worst_id"],
                primary_comparison_id=primary,
                meta={"source": source.value, "target": target.value, "pooled": True},
            )
        else:

            def compare_fn(vp: Dict[str, Any]) -> Dict[str, Any]:
                report = engine.compare(
                    CompareRequest(
                        source=source,
                        target=target,
                        viewport=vp,
                        options=options,
                    )
                )
                return report.to_dict()

            suite_report = run_pixel_perfect(
                compare_fn=compare_fn,
                suite=str(suite) if suite else None,
                viewports=viewports,
                target_similarity=target_sim,
                include_reports=True,
                meta={"source": source.value, "target": target.value},
            )

        persist_suite_report(engine.artifacts_root, suite_report)
        payload = suite_report.to_dict()
        primary = None
        for vr in suite_report.viewports:
            if vr.comparison_id == suite_report.primary_comparison_id and vr.report:
                primary = vr.report
                break
        if primary is None:
            for vr in suite_report.viewports:
                if vr.report:
                    primary = vr.report
                    break
        return 200, {
            "ok": True,
            "suite": payload,
            "report": primary or payload,
            "reports": [v.report for v in suite_report.viewports if v.report],
        }
    except FileNotFoundError as exc:
        return 404, {"error": str(exc)}
    except (ValueError, VisualEngineBridgeError) as exc:
        return 400, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": str(exc)}


def handle_cleanup(engine: VisualEngine, data: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
    from .cleanup import cleanup_artifacts, cleanup_stats
    from . import telemetry

    data = data or {}
    try:
        result = cleanup_artifacts(
            engine.artifacts_root,
            max_age_sec=float(data.get("max_age_sec") or data.get("maxAgeSec") or 7 * 24 * 3600),
            max_comparisons=int(data.get("max_comparisons") or data.get("maxComparisons") or 80),
            dry_run=bool(data.get("dry_run") or data.get("dryRun")),
        )
        telemetry.record("cleanup", ok=True)
        result["stats"] = cleanup_stats(engine.artifacts_root)
        return 200, result
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": str(exc)}


def handle_cleanup_stats(engine: VisualEngine) -> Tuple[int, Dict[str, Any]]:
    from .cleanup import cleanup_stats
    from . import telemetry

    return 200, {
        "ok": True,
        "stats": cleanup_stats(engine.artifacts_root),
        "telemetry": telemetry.snapshot(),
    }


def handle_mockup_upload(engine: VisualEngine, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Save a mockup image under mockups/ (PNG preferred, max 5 MB)."""
    import base64
    import re
    import time
    import unicodedata

    raw_name = str(data.get("name") or data.get("filename") or "mockup.png").strip()
    raw_name = unicodedata.normalize("NFKD", raw_name)
    safe = re.sub(r"[^\w.\-]+", "_", raw_name, flags=re.UNICODE).strip("._") or "mockup.png"
    if not safe.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        safe = f"{Path(safe).stem}.png"
    mime = str(data.get("mime") or "").lower()
    b64 = data.get("content_base64")
    if not isinstance(b64, str) or not b64.strip():
        return 400, {"error": "content_base64 is required"}
    try:
        payload = base64.b64decode(b64, validate=False)
    except Exception as exc:  # noqa: BLE001
        return 400, {"error": f"invalid base64: {exc}"}
    if len(payload) > 5_000_000:
        return 413, {"error": "mockup muito grande (máx. 5 MB)"}
    # Magic-byte sniff (reject HTML/JS uploads)
    head = payload[:16]
    is_png = head.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = head[:3] == b"\xff\xd8\xff"
    is_webp = head[:4] == b"RIFF" and b"WEBP" in payload[:16]
    if not (is_png or is_jpeg or is_webp):
        return 400, {"error": "arquivo deve ser PNG, JPEG ou WebP"}
    if not is_png and "png" in mime:
        return 400, {"error": "mime indica PNG mas o conteúdo não é PNG"}
    # Prefer PNG for pixelmatch — still store others, warn.
    mockups = engine.project_dir / "mockups"
    mockups.mkdir(parents=True, exist_ok=True)
    target = mockups / safe
    if target.exists():
        stamp = str(int(time.time()))[-6:]
        target = mockups / f"{Path(safe).stem}_{stamp}{Path(safe).suffix}"
    target.write_bytes(payload)
    rel = str(target.relative_to(engine.project_dir)).replace("\\", "/")
    return 201, {
        "ok": True,
        "path": rel,
        "bytes": len(payload),
        "format": "png" if is_png else ("jpeg" if is_jpeg else "webp"),
        "warning": None if is_png else "Comparação pixelmatch funciona melhor com PNG — a UI converte no upload.",
    }


def resolve_artifact_file(engine: VisualEngine, comparison_id: str, filename: str) -> Optional[Path]:
    cid = str(comparison_id or "").strip()
    name = str(filename or "").strip().replace("\\", "/").split("/")[-1]
    if not cid or not name or ".." in cid or ".." in name:
        return None
    allowed = {
        "reference.png",
        "actual.png",
        "diff.png",
        "overlay.png",
        "reference-normalized.png",
        "actual-normalized.png",
        "report.json",
        "metadata.json",
        "dom-diff.json",
        "layout-diff.json",
        "baseline.png",
        "meta.json",
    }
    if name not in allowed:
        return None
    # Baseline artifacts live under baselines/<routeId>/
    if cid.startswith("baselines/"):
        rel = cid[len("baselines/") :].strip("/")
        if not rel or "/" in rel or ".." in rel:
            return None
        path = (engine.artifacts_root / "baselines" / rel / name).resolve()
    else:
        path = (engine.artifacts_root / cid / name).resolve()
    try:
        path.relative_to(engine.artifacts_root.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def resolve_baseline_file(engine: VisualEngine, route_id: str, filename: str = "baseline.png") -> Optional[Path]:
    from .baselines import sanitize_route_id

    try:
        rid = sanitize_route_id(route_id)
    except ValueError:
        return None
    return resolve_artifact_file(engine, f"baselines/{rid}", filename)


def guess_content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    return ctype or "application/octet-stream"


def handle_correction_start(
    engine: VisualEngine,
    data: Dict[str, Any],
    *,
    host_header: str,
) -> Tuple[int, Dict[str, Any]]:
    """Start a background correction loop (mockup vs preview by default)."""
    from .correction import CorrectionConfig, correction_manager

    from local_agent.security import resolve_in_workspace

    mockup = str(data.get("mockup") or data.get("reference") or "").strip()
    if not mockup:
        return 400, {"error": "mockup path is required"}
    try:
        mockup_path = resolve_in_workspace(engine.project_dir, mockup)
    except Exception as exc:  # noqa: BLE001
        return 400, {"error": f"invalid mockup path: {exc}"}
    if not mockup_path.is_file():
        return 404, {"error": f"mockup not found: {mockup}"}

    cfg_raw = data.get("config") if isinstance(data.get("config"), dict) else {}
    strategy_early = str(data.get("strategy") or data.get("correction_strategy") or "css").strip().lower()
    if strategy_early in {"mockup", "mockup-to-code", "image-to-code", "i2c"}:
        strategy_early = "agent"
    default_timeout = 1800 if strategy_early in {"agent", "hybrid"} else 600
    default_attempts = 4 if strategy_early in {"agent", "hybrid"} else 5
    config = CorrectionConfig(
        target_similarity=float(cfg_raw.get("target_similarity") or data.get("target_similarity") or 0.95),
        max_attempts=int(cfg_raw.get("max_attempts") or data.get("max_attempts") or default_attempts),
        min_improvement=float(cfg_raw.get("min_improvement") or data.get("min_improvement") or 0.005),
        stagnation_limit=int(cfg_raw.get("stagnation_limit") or data.get("stagnation_limit") or 2),
        timeout_sec=float(cfg_raw.get("timeout_sec") or data.get("timeout_sec") or default_timeout),
    )
    viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else {"width": 1366, "height": 768}
    suite = str(data.get("suite") or "").strip() or None
    viewports = data.get("viewports") if isinstance(data.get("viewports"), list) else None
    options = data.get("options") if isinstance(data.get("options"), dict) else {}
    options = {
        **options,
        "fit": options.get("fit") or data.get("fit") or "contain",
        "includeDomDiff": True,
        "includeLayout": True,
    }
    # Correction preview mode (auto/dev) — not pixel_perfect suite mode.
    preview_mode = str(data.get("preview_mode") or data.get("mode") or "auto")
    if preview_mode in {"pixel_perfect", "pixel-perfect"}:
        preview_mode = "auto"
    file_path = str(data.get("path") or "index.html")
    strategy = str(data.get("strategy") or data.get("correction_strategy") or "css").strip().lower()
    if strategy in {"mockup", "mockup-to-code", "image-to-code", "i2c"}:
        strategy = "agent"
    if strategy not in {"css", "agent", "hybrid"}:
        strategy = "css"
    max_agent_steps = int(data.get("max_agent_steps") or data.get("agent_max_steps") or 12)
    stack_hint = str(data.get("stack") or data.get("stack_hint") or "").strip()
    settle_seconds = float(data.get("settle_seconds") or data.get("preview_settle_seconds") or 1.6)

    def compare_fn() -> Dict[str, Any]:
        preview_url = engine.resolve_preview_url(
            host_header=host_header,
            mode=preview_mode,
            file_path=file_path,
        )
        if suite or (viewports and len(viewports) > 1):
            from .pixel_perfect import run_pixel_perfect

            def per_vp(vp: Dict[str, Any]) -> Dict[str, Any]:
                return engine.compare(
                    CompareRequest(
                        source=Side(type="image", value=mockup),
                        target=Side(type="url", value=preview_url),
                        viewport=vp,
                        options=options,
                    )
                ).to_dict()

            suite_report = run_pixel_perfect(
                compare_fn=per_vp,
                suite=suite,
                viewports=viewports,
                target_similarity=config.target_similarity,
                include_reports=False,
            )
            # Drive the loop by the worst viewport score.
            return {
                "comparisonId": suite_report.primary_comparison_id,
                "similarity": suite_report.min_similarity,
                "status": suite_report.status,
                "mode": "pixel_perfect",
                "suite": suite_report.to_dict(),
                "layoutChanges": [],
                "regions": [],
            }

        report = engine.compare(
            CompareRequest(
                source=Side(type="image", value=mockup),
                target=Side(type="url", value=preview_url),
                viewport=viewport,
                options=options,
            )
        )
        return report.to_dict()

    plan_fn = None
    apply_fn = None
    rollback_fn = None
    job_holder: Dict[str, Any] = {"job": None}
    if strategy in {"agent", "hybrid"}:
        from .image_to_code import make_agent_strategy_fns

        def cancel_check() -> bool:
            job = job_holder.get("job")
            return bool(job and getattr(job, "cancel_requested", False))

        def on_agent_event(ev: Dict[str, Any]) -> None:
            job = job_holder.get("job")
            if not job:
                return
            payload = dict(ev or {})
            payload.setdefault("ts", time.time())
            job.events.append(payload)

        fns = make_agent_strategy_fns(
            engine.project_dir,
            mockup=mockup,
            strategy=strategy,
            target_similarity=config.target_similarity,
            max_agent_steps=max_agent_steps,
            stack_hint=stack_hint,
            settle_seconds=settle_seconds,
            cancel_check=cancel_check,
            on_event=on_agent_event,
        )
        plan_fn = fns["plan_fn"]
        apply_fn = fns["apply_fn"]
        rollback_fn = fns["rollback_fn"]

    try:
        job = correction_manager.start_background(
            project_id=engine.project_id,
            workspace=engine.project_dir,
            compare_fn=compare_fn,
            config=config,
            meta={
                "mockup": mockup,
                "mode": preview_mode,
                "path": file_path,
                "viewport": viewport,
                "suite": suite,
                "strategy": strategy,
                "max_agent_steps": max_agent_steps,
                "stack": stack_hint or None,
                "settle_seconds": settle_seconds,
            },
            persist_dir=engine.artifacts_root / "corrections",
            plan_fn=plan_fn,
            apply_fn=apply_fn,
            rollback_fn=rollback_fn,
        )
        job_holder["job"] = job
    except RuntimeError as exc:
        return 409, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": str(exc)}
    return 202, {"ok": True, "correction": job.to_dict()}


def handle_correction_get(engine: VisualEngine, correction_id: str) -> Tuple[int, Dict[str, Any]]:
    from .correction import correction_manager

    job = correction_manager.get(correction_id)
    if job and job.project_id == engine.project_id:
        return 200, {"ok": True, "correction": job.to_dict()}
    # Disk fallback
    path = engine.artifacts_root / "corrections" / f"{correction_id}.json"
    if path.is_file():
        try:
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            return 200, {"ok": True, "correction": data}
        except (OSError, json.JSONDecodeError):
            pass
    return 404, {"error": "correction not found"}


def handle_correction_cancel(engine: VisualEngine, correction_id: str) -> Tuple[int, Dict[str, Any]]:
    from .correction import correction_manager

    job = correction_manager.cancel(correction_id)
    if not job or job.project_id != engine.project_id:
        return 404, {"error": "correction not found"}
    return 200, {"ok": True, "correction": job.to_dict()}


def handle_correction_active(engine: VisualEngine) -> Tuple[int, Dict[str, Any]]:
    from .correction import correction_manager

    job = correction_manager.active_for_project(engine.project_id)
    return 200, {"ok": True, "correction": job.to_dict() if job else None}


def handle_list_baselines(engine: VisualEngine) -> Tuple[int, Dict[str, Any]]:
    from .baselines import list_baselines

    return 200, {"ok": True, "baselines": list_baselines(engine.artifacts_root)}


def handle_get_baseline(engine: VisualEngine, route_id: str) -> Tuple[int, Dict[str, Any]]:
    from .baselines import get_baseline

    item = get_baseline(engine.artifacts_root, route_id)
    if not item:
        return 404, {"error": "baseline not found"}
    return 200, {"ok": True, "baseline": item}


def handle_approve_baseline(engine: VisualEngine, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    from .baselines import approve_baseline, find_comparison_actual, sanitize_route_id

    try:
        route_id = sanitize_route_id(str(data.get("routeId") or data.get("route_id") or data.get("route") or ""))
    except ValueError as exc:
        return 400, {"error": str(exc)}
    comparison_id = str(data.get("comparisonId") or data.get("comparison_id") or "").strip()
    prefer = str(data.get("prefer") or "actual")
    if prefer not in {"actual", "reference"}:
        prefer = "actual"
    try:
        if comparison_id:
            source = find_comparison_actual(engine.artifacts_root, comparison_id, prefer=prefer)
        elif data.get("path"):
            from local_agent.security import resolve_in_workspace

            source = resolve_in_workspace(engine.project_dir, str(data["path"]))
            if not source.is_file():
                return 404, {"error": f"image not found: {data['path']}"}
        else:
            return 400, {"error": "comparisonId or path is required"}
        baseline = approve_baseline(
            engine.artifacts_root,
            route_id=route_id,
            source_png=source,
            comparison_id=comparison_id,
            viewport=data.get("viewport") if isinstance(data.get("viewport"), dict) else None,
            label=str(data.get("label") or ""),
            notes=str(data.get("notes") or ""),
        )
        return 200, {"ok": True, "baseline": baseline}
    except FileNotFoundError as exc:
        return 404, {"error": str(exc)}
    except ValueError as exc:
        return 400, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": str(exc)}


def handle_reject_baseline(engine: VisualEngine, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    from .baselines import reject_baseline, sanitize_route_id

    try:
        route_id = sanitize_route_id(str(data.get("routeId") or data.get("route_id") or data.get("route") or ""))
    except ValueError as exc:
        return 400, {"error": str(exc)}
    try:
        baseline = reject_baseline(
            engine.artifacts_root,
            route_id=route_id,
            comparison_id=str(data.get("comparisonId") or data.get("comparison_id") or ""),
            notes=str(data.get("notes") or ""),
            remove_image=bool(data.get("remove_image") or data.get("removeImage")),
        )
        return 200, {"ok": True, "baseline": baseline}
    except ValueError as exc:
        return 400, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 500, {"error": str(exc)}


def handle_delete_baseline(engine: VisualEngine, route_id: str) -> Tuple[int, Dict[str, Any]]:
    from .baselines import delete_baseline, sanitize_route_id

    try:
        rid = sanitize_route_id(route_id)
    except ValueError as exc:
        return 400, {"error": str(exc)}
    removed = delete_baseline(engine.artifacts_root, rid)
    if not removed:
        return 404, {"error": "baseline not found"}
    return 200, {"ok": True, "deleted": rid}


def handle_compare_baseline(
    engine: VisualEngine,
    data: Dict[str, Any],
    *,
    host_header: str,
) -> Tuple[int, Dict[str, Any]]:
    """Compare current preview (or URL) against an approved baseline route."""
    from .baselines import get_baseline, sanitize_route_id

    try:
        route_id = sanitize_route_id(str(data.get("routeId") or data.get("route_id") or data.get("route") or ""))
    except ValueError as exc:
        return 400, {"error": str(exc)}
    baseline = get_baseline(engine.artifacts_root, route_id)
    if not baseline or not baseline.get("hasBaseline"):
        return 404, {"error": f"no approved baseline for route: {route_id}"}
    target_sim = float(data.get("target_similarity") or data.get("targetSimilarity") or 0.95)
    viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else baseline.get("viewport") or {
        "width": 1366,
        "height": 768,
    }
    options = data.get("options") if isinstance(data.get("options"), dict) else {}
    options = {**options, "fit": options.get("fit") or data.get("fit") or "contain"}
    # Build compare payload: baseline image vs preview/url
    payload = {
        "source": {"type": "image", "value": baseline["path"]},
        "target": data.get("target"),
        "viewport": viewport,
        "options": options,
        "mode": data.get("mode") or "auto",
        "path": data.get("path") or "index.html",
    }
    if not payload["target"]:
        if data.get("url"):
            payload["target"] = {"type": "url", "value": str(data["url"])}
        else:
            payload["target"] = {
                "type": "url",
                "value": engine.resolve_preview_url(
                    host_header=host_header,
                    mode=str(payload["mode"]),
                    file_path=str(payload["path"]),
                ),
            }
    code, result = handle_compare(engine, payload, host_header=host_header)
    if code != 200:
        return code, result
    report = result.get("report") or {}
    sim = report.get("similarity")
    passed = isinstance(sim, (int, float)) and float(sim) >= target_sim
    result["baseline"] = {
        "routeId": route_id,
        "targetSimilarity": target_sim,
        "passed": passed,
        "status": "passed" if passed else "failed",
        "path": baseline["path"],
    }
    return 200, result
