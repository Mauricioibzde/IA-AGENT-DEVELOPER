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
