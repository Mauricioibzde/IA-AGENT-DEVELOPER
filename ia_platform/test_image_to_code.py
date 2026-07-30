"""Tests for mockup → code goal builders and agent/hybrid strategy planning."""

from __future__ import annotations

from pathlib import Path

from ia_platform.visual_engine.image_to_code import (
    build_bootstrap_goal,
    build_correction_goal,
    make_agent_strategy_fns,
    needs_bootstrap,
    summarize_visual_diff,
)


def test_needs_bootstrap_thresholds() -> None:
    assert needs_bootstrap(None) is True
    assert needs_bootstrap({"similarity": 0.2}) is True
    assert needs_bootstrap({"similarity": 0.8}) is False


def test_build_bootstrap_goal_mentions_mockup() -> None:
    goal = build_bootstrap_goal("mockups/home.png", workspace_files=["index.html", "styles.css"])
    assert "mockups/home.png" in goal
    assert "IMAGE-TO-CODE" in goal
    assert "index.html" in goal
    assert "pixel" in goal.lower() or "fiel" in goal.lower()


def test_build_correction_goal_includes_diff_feedback() -> None:
    report = {
        "similarity": 0.72,
        "summary": {"diffPercent": 0.18},
        "comparisonId": "cmp-1",
        "artifacts": {"diff": "artifacts/cmp-1/diff.png", "actual": "artifacts/cmp-1/actual.png"},
        "layoutChanges": [{"selector": ".hero", "delta": {"width": 20, "height": 0, "x": 0, "y": 0}}],
        "regions": [
            {
                "category": "typography",
                "probableElement": {"selector": "h1", "confidence": "high"},
            }
        ],
    }
    summary = summarize_visual_diff(report)
    assert ".hero" in summary
    assert "h1" in summary
    assert "cmp-1" in summary
    goal = build_correction_goal("mockups/home.png", report, attempt=2, target_similarity=0.95)
    assert "CORREÇÃO VISUAL" in goal
    assert "mockups/home.png" in goal
    assert ".hero" in goal
    assert "95%" in goal
    assert "Checklist prioritário" in goal
    assert "`h1`" in goal


def test_detect_stack_and_file_inventory(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"dependencies":{"react":"18.0.0"}}', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.tsx").write_text("export default function App(){return null}", encoding="utf-8")
    from ia_platform.visual_engine.image_to_code import detect_stack_hint, list_workspace_files

    assert detect_stack_hint(tmp_path) == "react"
    files = list_workspace_files(tmp_path)
    assert any(f.endswith("App.tsx") for f in files)


def test_agent_plan_fn_bootstraps_then_refines(tmp_path: Path) -> None:
    fns = make_agent_strategy_fns(
        tmp_path,
        mockup="mockups/ui.png",
        strategy="agent",
        target_similarity=0.95,
    )
    bootstrap_patches = fns["plan_fn"]({"similarity": 0.1})
    assert bootstrap_patches and bootstrap_patches[0]["kind"] == "agent"
    assert bootstrap_patches[0]["mode"] == "bootstrap"
    assert "mockups/ui.png" in bootstrap_patches[0]["goal"]

    refine_patches = fns["plan_fn"](
        {
            "similarity": 0.7,
            "layoutChanges": [{"selector": ".card", "delta": {"width": 8, "height": 0, "x": 0, "y": 0}}],
        }
    )
    assert refine_patches[0]["kind"] == "agent"
    assert refine_patches[0]["mode"] == "refine"
    assert ".card" in refine_patches[0]["goal"]


def test_hybrid_plan_prefers_css_when_close(tmp_path: Path) -> None:
    fns = make_agent_strategy_fns(
        tmp_path,
        mockup="mockups/ui.png",
        strategy="hybrid",
    )
    patches = fns["plan_fn"](
        {
            "similarity": 0.82,
            "layoutChanges": [{"selector": ".box", "delta": {"width": 12, "height": 0, "x": 0, "y": 0}}],
            "regions": [],
        }
    )
    assert patches
    assert patches[0].get("kind") != "agent"
    assert patches[0].get("selector") == ".box"


def test_agent_apply_uses_runner_and_records_run(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_run(workspace, goal, **kwargs):
        calls.append({"workspace": Path(workspace), "goal": goal, **kwargs})
        (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
        return {
            "ok": True,
            "run_id": kwargs.get("preferred_run_id") or "agent-1",
            "status": "SUCCESS",
            "created_files": ["index.html"],
            "modified_files": [],
            "summary": "ok",
        }

    monkeypatch.setattr(
        "ia_platform.visual_engine.image_to_code.run_agent_step",
        fake_run,
    )
    fns = make_agent_strategy_fns(tmp_path, mockup="mockups/a.png", strategy="agent")
    patches = fns["plan_fn"]({"similarity": 0.2})
    result = fns["apply_fn"](patches, "corr-job-1")
    assert result["ok"] is True
    assert result["kind"] == "agent"
    assert "index.html" in result["written"]
    assert calls and "IMAGE-TO-CODE" in calls[0]["goal"]
