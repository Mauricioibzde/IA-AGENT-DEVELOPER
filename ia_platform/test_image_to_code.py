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
    assert needs_bootstrap({"similarity": 0.5}) is True
    assert needs_bootstrap({"similarity": 0.8}) is False


def test_build_bootstrap_goal_mentions_mockup() -> None:
    goal = build_bootstrap_goal("mockups/home.png", workspace_files=["index.html", "styles.css"])
    assert "mockups/home.png" in goal
    assert "IMAGE-TO-CODE" in goal
    assert "index.html" in goal
    assert "pixel" in goal.lower() or "fiel" in goal.lower()


def test_build_bootstrap_goal_injects_vision_spec() -> None:
    goal = build_bootstrap_goal(
        "mockups/home.png",
        vision_spec="## Layout\n- sidebar esquerda escura\n- main com chat",
    )
    assert "Especificação visual" in goal
    assert "sidebar esquerda escura" in goal


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


def test_build_correction_goal_includes_vision_reminder() -> None:
    goal = build_correction_goal(
        "mockups/a.png",
        {"similarity": 0.6},
        vision_spec="## Cores\n- fundo #0b0f14",
    )
    assert "especificação visual" in goal.lower()
    assert "#0b0f14" in goal


def test_build_correction_goal_includes_palette_and_diff_vision() -> None:
    goal = build_correction_goal(
        "mockups/a.png",
        {"similarity": 0.55, "artifacts": {"diff": ".agent/visual/c1/diff.png"}},
        palette_block="## Paleta amostrada do mockup\n- #0b0f14 (~60%)",
        vision_diff="## Diagnóstico visual mockup × preview\n- resumo: sidebar clara demais",
    )
    assert "#0b0f14" in goal
    assert "Diagnóstico visual" in goal
    assert "sidebar clara" in goal


def test_agent_plan_injects_palette_without_vision(tmp_path: Path, monkeypatch) -> None:
    mockups = tmp_path / "mockups"
    mockups.mkdir()
    (mockups / "ui.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 24)

    monkeypatch.setattr(
        "ia_platform.visual_engine.palette.sample_palette",
        lambda path, **kwargs: {
            "ok": True,
            "colors": [{"hex": "#112233", "pct": 0.7}],
        },
    )
    fns = make_agent_strategy_fns(
        tmp_path,
        mockup="mockups/ui.png",
        strategy="agent",
        use_vision=False,
    )
    patches = fns["plan_fn"]({"similarity": 0.1})
    assert patches[0]["has_palette"] is True
    assert "#112233" in patches[0]["goal"]


def test_agent_plan_injects_vision_into_goal(tmp_path: Path, monkeypatch) -> None:
    events = []

    def fake_describe(workspace, mockup, **kwargs):
        if kwargs.get("on_event"):
            kwargs["on_event"]({"type": "vision.completed", "model": "llava", "chars": 42})
        return {
            "ok": True,
            "spec": "## Layout\n- rail lateral + canvas central",
            "model": "llava:7b",
            "cached": False,
            "path": mockup,
        }

    monkeypatch.setattr(
        "ia_platform.visual_engine.vision.describe_mockup",
        fake_describe,
    )
    fns = make_agent_strategy_fns(
        tmp_path,
        mockup="mockups/ui.png",
        strategy="agent",
        use_vision=True,
        on_event=events.append,
    )
    patches = fns["plan_fn"]({"similarity": 0.1})
    assert patches[0]["has_vision_spec"] is True
    assert patches[0]["vision_model"] == "llava:7b"
    assert "rail lateral" in patches[0]["goal"]


def test_agent_plan_injects_vision_diff_on_refine(tmp_path: Path, monkeypatch) -> None:
    actual = tmp_path / "actual.png"
    actual.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    mockups = tmp_path / "mockups"
    mockups.mkdir()
    (mockups / "ui.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)

    monkeypatch.setattr(
        "ia_platform.visual_engine.palette.sample_palette",
        lambda path, **kwargs: {"ok": True, "colors": [{"hex": "#010101", "pct": 0.9}]},
    )
    monkeypatch.setattr(
        "ia_platform.visual_engine.vision.describe_mockup",
        lambda *a, **k: {"ok": True, "spec": "## Layout\n- ok", "model": "llava", "structured": {}},
    )

    def fake_diff(*a, **k):
        if k.get("on_event"):
            k["on_event"]({"type": "vision.diff_completed", "preview": "diff preview", "fixes": 2})
        return {
            "ok": True,
            "spec": "## Diagnóstico visual mockup × preview\n- resumo: header desalinhado",
            "model": "llava",
            "structured": {"summary": "header desalinhado"},
        }

    monkeypatch.setattr(
        "ia_platform.visual_engine.vision.compare_mockup_vs_actual",
        fake_diff,
    )
    events = []
    fns = make_agent_strategy_fns(
        tmp_path,
        mockup="mockups/ui.png",
        strategy="agent",
        use_vision=True,
        on_event=events.append,
    )
    # Force refine path (above bootstrap threshold).
    patches = fns["plan_fn"](
        {
            "similarity": 0.7,
            "comparisonId": "cmp-refine-1",
            "artifacts": {"actual": str(actual)},
        }
    )
    assert patches[0]["mode"] == "refine"
    assert patches[0]["has_vision_diff"] is True
    assert "header desalinhado" in patches[0]["goal"]


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
        use_vision=False,
    )
    # Attempt 1 (odd): agent refine/bootstrap path even when close.
    first = fns["plan_fn"](
        {
            "similarity": 0.88,
            "layoutChanges": [{"selector": ".box", "delta": {"width": 12, "height": 0, "x": 0, "y": 0}}],
            "regions": [],
        }
    )
    assert first and first[0].get("kind") == "agent"
    # Attempt 2 (even) + high similarity + layout delta → meaningful CSS.
    patches = fns["plan_fn"](
        {
            "similarity": 0.88,
            "layoutChanges": [{"selector": ".box", "delta": {"width": 12, "height": 0, "x": 0, "y": 0}}],
            "regions": [],
        }
    )
    assert patches
    assert patches[0].get("kind") != "agent"
    assert patches[0].get("selector") == ".box"


def test_hybrid_plan_keeps_agent_at_mid_fidelity(tmp_path: Path) -> None:
    fns = make_agent_strategy_fns(
        tmp_path,
        mockup="mockups/ui.png",
        strategy="hybrid",
        use_vision=False,
    )
    patches = fns["plan_fn"](
        {
            "similarity": 0.7,
            "layoutChanges": [{"selector": ".box", "delta": {"width": 12, "height": 0, "x": 0, "y": 0}}],
            "regions": [],
        }
    )
    assert patches[0].get("kind") == "agent"


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
