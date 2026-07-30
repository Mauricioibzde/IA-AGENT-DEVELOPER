"""HTTP helpers for Visual Engine routes (used by PlatformHandler)."""

from __future__ import annotations

import mimetypes
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
        # Multi-viewport: run sequential compares and aggregate (Phase 2 basic)
        viewports = data.get("viewports")
        options = data.get("options") if isinstance(data.get("options"), dict) else {}
        if isinstance(viewports, list) and len(viewports) > 1:
            results = []
            for vp in viewports[:8]:
                if not isinstance(vp, dict):
                    continue
                report = engine.compare(
                    CompareRequest(
                        source=source,
                        target=target,
                        viewport=vp,
                        options=options,
                        comparison_id=data.get("comparisonId"),
                    )
                )
                results.append(report.to_dict())
            if not results:
                return 400, {"error": "no valid viewports"}
            return 200, {"ok": True, "reports": results, "report": results[0]}

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
    }
    if name not in allowed:
        return None
    path = (engine.artifacts_root / cid / name).resolve()
    try:
        path.relative_to(engine.artifacts_root.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


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
    config = CorrectionConfig(
        target_similarity=float(cfg_raw.get("target_similarity") or data.get("target_similarity") or 0.95),
        max_attempts=int(cfg_raw.get("max_attempts") or data.get("max_attempts") or 5),
        min_improvement=float(cfg_raw.get("min_improvement") or data.get("min_improvement") or 0.005),
        stagnation_limit=int(cfg_raw.get("stagnation_limit") or data.get("stagnation_limit") or 2),
        timeout_sec=float(cfg_raw.get("timeout_sec") or data.get("timeout_sec") or 600),
    )
    viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else {"width": 1366, "height": 768}
    options = data.get("options") if isinstance(data.get("options"), dict) else {}
    options = {
        **options,
        "fit": options.get("fit") or data.get("fit") or "contain",
        "includeDomDiff": True,
        "includeLayout": True,
    }
    mode = str(data.get("mode") or "auto")
    file_path = str(data.get("path") or "index.html")

    def compare_fn() -> Dict[str, Any]:
        preview_url = engine.resolve_preview_url(
            host_header=host_header,
            mode=mode,
            file_path=file_path,
        )
        report = engine.compare(
            CompareRequest(
                source=Side(type="image", value=mockup),
                target=Side(type="url", value=preview_url),
                viewport=viewport,
                options=options,
            )
        )
        return report.to_dict()

    try:
        job = correction_manager.start_background(
            project_id=engine.project_id,
            workspace=engine.project_dir,
            compare_fn=compare_fn,
            config=config,
            meta={"mockup": mockup, "mode": mode, "path": file_path, "viewport": viewport},
            persist_dir=engine.artifacts_root / "corrections",
        )
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
