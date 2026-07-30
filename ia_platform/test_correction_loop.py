"""Phase 5 correction loop unit tests (no browser / Node required)."""

from __future__ import annotations

from pathlib import Path

from ia_platform.visual_engine.correction import CorrectionConfig, CorrectionJob, CorrectionLoop
from ia_platform.visual_engine.patches import apply_patches, plan_heuristic_patches, rollback_patches


def test_plan_heuristic_patches_from_layout() -> None:
    report = {
        "similarity": 0.8,
        "layoutChanges": [
            {
                "selector": ".sidebar",
                "delta": {"x": 0, "y": 0, "width": 16, "height": 0},
            }
        ],
        "regions": [
            {
                "id": "region-1",
                "category": "layout",
                "probableElement": {"selector": ".hero", "confidence": "high"},
            }
        ],
    }
    patches = plan_heuristic_patches(report)
    assert patches
    assert any(p["selector"] == ".sidebar" for p in patches)


def test_plan_heuristic_patches_from_raw_bridge_payload() -> None:
    """VisualReport.to_dict used to bury layoutChanges under raw — patches must still see them."""
    report = {
        "comparison_id": "c1",
        "status": "done",
        "mode": "image-url",
        "similarity": 0.72,
        "raw": {
            "comparisonId": "c1",
            "similarity": 0.72,
            "layoutChanges": [
                {"selector": ".card", "delta": {"x": 8, "y": 0, "width": 0, "height": 12}}
            ],
            "regions": [
                {
                    "id": "region-2",
                    "category": "typography",
                    "probableElement": {"selector": "h1", "confidence": "medium"},
                }
            ],
        },
    }
    patches = plan_heuristic_patches(report)
    assert any(p["selector"] == ".card" for p in patches)
    assert any(p["selector"] == "h1" for p in patches)


def test_visual_report_to_dict_promotes_bridge_fields() -> None:
    from ia_platform.visual_engine.models import VisualReport

    report = VisualReport.from_bridge(
        {
            "comparisonId": "abc",
            "status": "done",
            "mode": "image-url",
            "similarity": 0.81,
            "layoutChanges": [{"selector": ".nav", "delta": {"width": 4}}],
            "regions": [{"id": "region-1", "category": "layout"}],
            "artifacts": {"diff": "diff.png"},
        }
    )
    data = report.to_dict()
    assert data["comparisonId"] == "abc"
    assert data["layoutChanges"][0]["selector"] == ".nav"
    assert data["regions"][0]["id"] == "region-1"
    assert data["raw"]["comparisonId"] == "abc"


def test_worst_viewport_patch_signal_keeps_layout() -> None:
    from types import SimpleNamespace

    from ia_platform.visual_engine.api import _worst_viewport_patch_signal

    suite = SimpleNamespace(
        viewports=[
            SimpleNamespace(
                similarity=0.9,
                comparison_id="good",
                viewport={"id": "desktop"},
                report={"layoutChanges": [], "regions": []},
            ),
            SimpleNamespace(
                similarity=0.7,
                comparison_id="bad",
                viewport={"id": "mobile"},
                report={
                    "layoutChanges": [{"selector": ".hero", "delta": {"width": 20}}],
                    "regions": [
                        {
                            "id": "region-1",
                            "probableElement": {"selector": ".hero", "confidence": "high"},
                        }
                    ],
                },
            ),
        ]
    )
    signal = _worst_viewport_patch_signal(suite)
    assert signal["comparisonId"] == "bad"
    assert signal["layoutChanges"][0]["selector"] == ".hero"
    assert signal["regions"]


def test_apply_and_rollback_patches(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        "<!DOCTYPE html><html><head></head><body><div class='x'></div></body></html>",
        encoding="utf-8",
    )
    patches = [
        {
            "kind": "css_rule",
            "selector": ".x",
            "declarations": ["color: red"],
            "reason": "test",
        }
    ]
    applied = apply_patches(tmp_path, patches, run_id="corr-test-1")
    assert applied["ok"] is True
    assert (tmp_path / "correction-overrides.css").is_file()
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "correction-overrides.css" in html
    restored = rollback_patches(tmp_path, "corr-test-1")
    assert restored["ok"] is True
    # Created css should be removed on rollback of created file.
    assert not (tmp_path / "correction-overrides.css").exists() or "color: red" not in (
        tmp_path / "correction-overrides.css"
    ).read_text(encoding="utf-8") if (tmp_path / "correction-overrides.css").exists() else True


def test_loop_accepts_improvement_and_rolls_back_worsening(tmp_path: Path) -> None:
    scores = iter([0.80, 0.88, 0.86, 0.93])

    def compare_fn():
        sim = next(scores)
        return {
            "comparisonId": f"c-{sim}",
            "similarity": sim,
            "layoutChanges": [
                {"selector": ".box", "delta": {"width": 10, "height": 0, "x": 0, "y": 0}}
            ],
            "regions": [],
        }

    applied: list[str] = []

    def apply_fn(patches, run_id):
        applied.append(run_id)
        return {"ok": True, "written": ["correction-overrides.css"], "patches": len(patches)}

    rolled: list[str] = []

    def rollback_fn(run_id):
        rolled.append(run_id)
        return {"ok": True, "restored": [], "removed": [], "skipped": []}

    job = CorrectionJob(id="j1", project_id="p1", config=CorrectionConfig(
        target_similarity=0.95,
        max_attempts=3,
        min_improvement=0.005,
        stagnation_limit=3,
        worsen_epsilon=0.002,
    ))
    loop = CorrectionLoop(
        tmp_path,
        compare_fn=compare_fn,
        apply_fn=apply_fn,
        rollback_fn=rollback_fn,
        config=job.config,
    )
    out = loop.run(job)
    assert out.baseline_similarity == 0.80
    assert out.best_similarity is not None and out.best_similarity >= 0.88
    assert any(a["status"] == "rolled_back" for a in out.attempts)
    assert rolled  # worsening attempt rolled back
    assert out.status in {"completed", "failed"}
    assert any(e["type"] == "correction.started" for e in out.events)
    assert any(e["type"].startswith("correction.") for e in out.events)


def test_loop_stops_when_already_at_target(tmp_path: Path) -> None:
    def compare_fn():
        return {"comparisonId": "ok", "similarity": 0.99, "layoutChanges": [], "regions": []}

    job = CorrectionJob(
        id="j2",
        project_id="p1",
        config=CorrectionConfig(target_similarity=0.95, max_attempts=3),
    )
    out = CorrectionLoop(tmp_path, compare_fn=compare_fn, config=job.config).run(job)
    assert out.status == "completed"
    assert out.attempts == []
    assert out.improvement == 0.0
