"""Phase 6 Pixel Perfect suite unit tests (no browser / Node required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ia_platform.visual_engine.pixel_perfect import (
    aggregate_scores,
    list_suites,
    persist_suite_report,
    resolve_suite_viewports,
    resolve_viewport,
    run_pixel_perfect,
    ViewportResult,
)


def test_list_suites_contains_responsive() -> None:
    suites = list_suites()
    ids = {s["id"] for s in suites}
    assert "responsive" in ids
    assert "mobile" in ids
    resp = next(s for s in suites if s["id"] == "responsive")
    assert resp["count"] == 3


def test_resolve_viewport_preset_and_wxh() -> None:
    vp = resolve_viewport("iphone_15")
    assert vp["width"] == 393
    assert vp["height"] == 852
    custom = resolve_viewport("1366x768")
    assert custom["width"] == 1366
    assert custom["height"] == 768


def test_resolve_suite_viewports() -> None:
    sid, name, vps = resolve_suite_viewports(suite="responsive")
    assert sid == "responsive"
    assert len(vps) == 3
    with pytest.raises(ValueError):
        resolve_suite_viewports(suite="nope")


def test_run_pixel_perfect_pass_fail() -> None:
    scores = {
        "desktop_standard": 0.97,
        "ipad_air": 0.96,
        "iphone_15": 0.91,
    }

    def compare_fn(vp):
        return {
            "comparisonId": f"c-{vp['id']}",
            "similarity": scores[vp["id"]],
            "status": "ok",
        }

    report = run_pixel_perfect(
        compare_fn=compare_fn,
        suite="responsive",
        target_similarity=0.95,
        include_reports=True,
    )
    assert report.status == "failed"
    assert report.failed_count == 1
    assert report.passed_count == 2
    assert report.min_similarity == pytest.approx(0.91)
    assert report.worst_viewport_id == "iphone_15"
    assert report.primary_comparison_id == "c-iphone_15"


def test_run_pixel_perfect_all_pass() -> None:
    def compare_fn(vp):
        return {"comparisonId": vp["id"], "similarity": 0.99}

    report = run_pixel_perfect(compare_fn=compare_fn, suite="desktop", target_similarity=0.95)
    assert report.status == "passed"
    assert report.failed_count == 0
    assert report.min_similarity == pytest.approx(0.99)


def test_aggregate_and_persist(tmp_path: Path) -> None:
    results = [
        ViewportResult(
            viewport={"id": "a", "width": 1, "height": 1},
            similarity=0.9,
            passed=False,
            target_similarity=0.95,
            comparison_id="c1",
        ),
        ViewportResult(
            viewport={"id": "b", "width": 2, "height": 2},
            similarity=0.98,
            passed=True,
            target_similarity=0.95,
            comparison_id="c2",
        ),
    ]
    agg = aggregate_scores(results, target=0.95)
    assert agg["status"] == "failed"
    assert agg["worst_id"] == "a"

    from ia_platform.visual_engine.pixel_perfect import SuiteReport

    suite = SuiteReport(
        suite_id="responsive",
        suite_name="Responsivo",
        status="failed",
        target_similarity=0.95,
        viewports=results,
        min_similarity=0.9,
        avg_similarity=0.94,
        max_similarity=0.98,
        passed_count=1,
        failed_count=1,
        worst_viewport_id="a",
        primary_comparison_id="c1",
    )
    path = persist_suite_report(tmp_path, suite)
    assert path.is_file()
    hist = tmp_path / "history.json"
    assert hist.is_file()
