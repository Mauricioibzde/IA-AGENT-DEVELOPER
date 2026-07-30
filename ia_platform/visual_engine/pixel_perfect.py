"""Pixel Perfect Mode — multi-viewport suite compare with pass/fail targets (Phase 6)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

# Preset ids mirror visual_engine/src/viewports.js DEVICE_PRESETS.
VIEWPORT_PRESETS: Dict[str, Dict[str, Any]] = {
    "desktop_4k": {"id": "desktop_4k", "name": "Desktop 4K", "width": 3840, "height": 2160, "deviceScaleFactor": 1},
    "desktop_full_hd": {
        "id": "desktop_full_hd",
        "name": "Desktop Full HD",
        "width": 1920,
        "height": 1080,
        "deviceScaleFactor": 1,
    },
    "desktop_standard": {
        "id": "desktop_standard",
        "name": "Desktop Standard",
        "width": 1366,
        "height": 768,
        "deviceScaleFactor": 1,
    },
    "laptop_15": {"id": "laptop_15", "name": 'Laptop 15"', "width": 1440, "height": 900, "deviceScaleFactor": 1},
    "laptop_13": {"id": "laptop_13", "name": 'Laptop 13"', "width": 1280, "height": 800, "deviceScaleFactor": 1},
    "ipad_pro_12": {
        "id": "ipad_pro_12",
        "name": 'iPad Pro 12.9"',
        "width": 1024,
        "height": 1366,
        "deviceScaleFactor": 2,
    },
    "ipad_air": {"id": "ipad_air", "name": "iPad Air", "width": 820, "height": 1180, "deviceScaleFactor": 2},
    "ipad_mini": {"id": "ipad_mini", "name": "iPad Mini", "width": 768, "height": 1024, "deviceScaleFactor": 2},
    "iphone_15_pro_max": {
        "id": "iphone_15_pro_max",
        "name": "iPhone 15 Pro Max",
        "width": 430,
        "height": 932,
        "deviceScaleFactor": 3,
    },
    "iphone_15": {"id": "iphone_15", "name": "iPhone 15", "width": 393, "height": 852, "deviceScaleFactor": 3},
    "iphone_se": {"id": "iphone_se", "name": "iPhone SE", "width": 375, "height": 667, "deviceScaleFactor": 2},
    "samsung_galaxy_s24": {
        "id": "samsung_galaxy_s24",
        "name": "Samsung Galaxy S24",
        "width": 412,
        "height": 915,
        "deviceScaleFactor": 2.625,
    },
    "mobile_small": {
        "id": "mobile_small",
        "name": "Mobile small (320px)",
        "width": 320,
        "height": 568,
        "deviceScaleFactor": 2,
    },
}

PIXEL_PERFECT_SUITES: Dict[str, Dict[str, Any]] = {
    "responsive": {
        "id": "responsive",
        "name": "Responsivo",
        "description": "Desktop + tablet + mobile",
        "viewports": ["desktop_standard", "ipad_air", "iphone_15"],
    },
    "desktop": {
        "id": "desktop",
        "name": "Desktop",
        "description": "Padrão, Full HD e laptop",
        "viewports": ["desktop_standard", "desktop_full_hd", "laptop_15"],
    },
    "mobile": {
        "id": "mobile",
        "name": "Mobile",
        "description": "Faixa estreita de smartphones",
        "viewports": ["iphone_15", "iphone_se", "samsung_galaxy_s24", "mobile_small"],
    },
    "full": {
        "id": "full",
        "name": "Completo",
        "description": "Desktop, laptop, tablet e mobile",
        "viewports": ["desktop_standard", "laptop_13", "ipad_air", "iphone_15"],
    },
}

DEFAULT_TARGET_SIMILARITY = 0.95
MAX_VIEWPORTS = 8

CompareFn = Callable[[Dict[str, Any]], Dict[str, Any]]
ViewportInput = Union[str, Dict[str, Any]]


@dataclass
class ViewportResult:
    viewport: Dict[str, Any]
    similarity: Optional[float]
    passed: bool
    target_similarity: float
    comparison_id: str = ""
    status: str = "unknown"
    error: Optional[str] = None
    report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.report is None:
            data.pop("report", None)
        return data


@dataclass
class SuiteReport:
    suite_id: str
    suite_name: str
    status: str  # passed | failed | error | partial
    target_similarity: float
    viewports: List[ViewportResult] = field(default_factory=list)
    min_similarity: Optional[float] = None
    avg_similarity: Optional[float] = None
    max_similarity: Optional[float] = None
    passed_count: int = 0
    failed_count: int = 0
    worst_viewport_id: Optional[str] = None
    primary_comparison_id: str = ""
    created_at: float = field(default_factory=time.time)
    duration_ms: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suiteId": self.suite_id,
            "suiteName": self.suite_name,
            "status": self.status,
            "targetSimilarity": self.target_similarity,
            "viewports": [v.to_dict() for v in self.viewports],
            "minSimilarity": self.min_similarity,
            "avgSimilarity": self.avg_similarity,
            "maxSimilarity": self.max_similarity,
            "passedCount": self.passed_count,
            "failedCount": self.failed_count,
            "worstViewportId": self.worst_viewport_id,
            "primaryComparisonId": self.primary_comparison_id,
            "createdAt": self.created_at,
            "durationMs": self.duration_ms,
            "meta": dict(self.meta),
            # Convenience aliases for UI / correction loop
            "similarity": self.min_similarity,
            "comparisonId": self.primary_comparison_id,
            "mode": "pixel_perfect",
        }


def list_suites() -> List[Dict[str, Any]]:
    out = []
    for suite in PIXEL_PERFECT_SUITES.values():
        vps = [resolve_viewport(v) for v in suite["viewports"]]
        out.append(
            {
                "id": suite["id"],
                "name": suite["name"],
                "description": suite["description"],
                "viewports": vps,
                "count": len(vps),
            }
        )
    return out


def resolve_viewport(raw: ViewportInput) -> Dict[str, Any]:
    if isinstance(raw, str):
        key = raw.strip()
        parts = key.lower().split("x")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return {
                "id": key,
                "name": key,
                "width": int(parts[0]),
                "height": int(parts[1]),
                "deviceScaleFactor": 1,
            }
        preset = VIEWPORT_PRESETS.get(key)
        if preset:
            return dict(preset)
        raise ValueError(f"unknown viewport preset: {raw}")
    if not isinstance(raw, dict):
        raise ValueError("viewport must be string id or object")
    if raw.get("id") and str(raw["id"]) in VIEWPORT_PRESETS and not raw.get("width"):
        return dict(VIEWPORT_PRESETS[str(raw["id"])])
    width = int(raw.get("width") or 1366)
    height = int(raw.get("height") or 768)
    dpr = float(raw.get("deviceScaleFactor") or 1)
    vid = str(raw.get("id") or f"{width}x{height}")
    return {
        "id": vid,
        "name": str(raw.get("name") or vid),
        "width": width,
        "height": height,
        "deviceScaleFactor": dpr,
    }


def resolve_suite_viewports(
    *,
    suite: Optional[str] = None,
    viewports: Optional[Sequence[ViewportInput]] = None,
) -> tuple[str, str, List[Dict[str, Any]]]:
    """Return (suite_id, suite_name, resolved viewports)."""
    if viewports:
        resolved = [resolve_viewport(v) for v in list(viewports)[:MAX_VIEWPORTS]]
        if not resolved:
            raise ValueError("no valid viewports")
        return "custom", "Custom", resolved
    sid = str(suite or "responsive").strip() or "responsive"
    meta = PIXEL_PERFECT_SUITES.get(sid)
    if not meta:
        raise ValueError(f"unknown suite: {sid}. Known: {', '.join(PIXEL_PERFECT_SUITES)}")
    resolved = [resolve_viewport(v) for v in meta["viewports"][:MAX_VIEWPORTS]]
    return meta["id"], meta["name"], resolved


def aggregate_scores(results: List[ViewportResult], *, target: float) -> Dict[str, Any]:
    scores = [r.similarity for r in results if isinstance(r.similarity, (int, float))]
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    worst_id = None
    if scores:
        worst = min(results, key=lambda r: r.similarity if r.similarity is not None else 2.0)
        worst_id = str(worst.viewport.get("id") or "")
    status = "passed" if scores and failed == 0 and all(r.error is None for r in results) else "failed"
    if not results:
        status = "error"
    elif any(r.error for r in results) and scores:
        status = "partial"
    elif not scores:
        status = "error"
    return {
        "min": min(scores) if scores else None,
        "avg": (sum(scores) / len(scores)) if scores else None,
        "max": max(scores) if scores else None,
        "passed": passed,
        "failed": failed,
        "worst_id": worst_id,
        "status": status,
        "target": target,
    }


def run_pixel_perfect(
    *,
    compare_fn: CompareFn,
    suite: Optional[str] = None,
    viewports: Optional[Sequence[ViewportInput]] = None,
    target_similarity: float = DEFAULT_TARGET_SIMILARITY,
    include_reports: bool = True,
    meta: Optional[Dict[str, Any]] = None,
) -> SuiteReport:
    """Run sequential per-viewport compares (one page/viewport via compare_fn).

    ``compare_fn(viewport)`` must return a report dict with ``similarity`` and ``comparisonId``.
    """
    t0 = time.time()
    suite_id, suite_name, resolved = resolve_suite_viewports(suite=suite, viewports=viewports)
    target = float(target_similarity)
    if target <= 0 or target > 1:
        raise ValueError("target_similarity must be in (0, 1]")

    results: List[ViewportResult] = []
    for vp in resolved:
        try:
            report = compare_fn(vp)
            if not isinstance(report, dict):
                raise ValueError("compare_fn must return a dict")
            sim = report.get("similarity")
            if sim is None and isinstance(report.get("summary"), dict):
                sim = report["summary"].get("similarity")
            sim_f = float(sim) if isinstance(sim, (int, float)) else None
            passed = sim_f is not None and sim_f >= target
            cid = str(report.get("comparisonId") or report.get("comparison_id") or "")
            results.append(
                ViewportResult(
                    viewport=vp,
                    similarity=sim_f,
                    passed=passed,
                    target_similarity=target,
                    comparison_id=cid,
                    status=str(report.get("status") or ("passed" if passed else "failed")),
                    report=report if include_reports else None,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                ViewportResult(
                    viewport=vp,
                    similarity=None,
                    passed=False,
                    target_similarity=target,
                    status="error",
                    error=str(exc),
                )
            )

    agg = aggregate_scores(results, target=target)
    # Primary = worst failing, else first
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

    return SuiteReport(
        suite_id=suite_id,
        suite_name=suite_name,
        status=str(agg["status"]),
        target_similarity=target,
        viewports=results,
        min_similarity=agg["min"],
        avg_similarity=agg["avg"],
        max_similarity=agg["max"],
        passed_count=int(agg["passed"]),
        failed_count=int(agg["failed"]),
        worst_viewport_id=agg["worst_id"],
        primary_comparison_id=primary,
        duration_ms=int((time.time() - t0) * 1000),
        meta=dict(meta or {}),
    )


def persist_suite_report(artifacts_root: Path, report: SuiteReport) -> Path:
    """Write suite report under .agent/visual/suites/<id>/report.json and history entry."""
    from .history import append_history

    root = Path(artifacts_root).resolve()
    run_id = f"suite-{uuid.uuid4().hex[:12]}"
    suite_dir = root / "suites" / run_id
    suite_dir.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    payload["id"] = run_id
    payload["comparisonId"] = run_id
    path = suite_dir / "report.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history(
        root,
        {
            "comparisonId": run_id,
            "mode": "pixel_perfect",
            "status": report.status,
            "similarity": report.min_similarity,
            "suiteId": report.suite_id,
            "suiteName": report.suite_name,
            "targetSimilarity": report.target_similarity,
            "passedCount": report.passed_count,
            "failedCount": report.failed_count,
            "worstViewportId": report.worst_viewport_id,
            "primaryComparisonId": report.primary_comparison_id,
            "createdAt": report.created_at,
            "durationMs": report.duration_ms,
        },
    )
    return path
