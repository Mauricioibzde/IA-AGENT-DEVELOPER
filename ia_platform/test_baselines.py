"""Phase 7 baseline approve/reject unit tests (no browser / Node required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ia_platform.visual_engine.baselines import (
    approve_baseline,
    delete_baseline,
    find_comparison_actual,
    get_baseline,
    list_baselines,
    reject_baseline,
    sanitize_route_id,
)
from ia_platform.visual_engine import api as visual_api
from ia_platform.visual_engine.service import VisualEngine

# Minimal valid 1×1 PNG
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_sanitize_route_id() -> None:
    assert sanitize_route_id("home") == "home"
    assert sanitize_route_id("home/index") == "home__index"
    with pytest.raises(ValueError):
        sanitize_route_id("../etc")


def test_approve_reject_list(tmp_path: Path) -> None:
    artifacts = tmp_path / ".agent" / "visual"
    artifacts.mkdir(parents=True)
    src = tmp_path / "shot.png"
    src.write_bytes(PNG_1X1)

    approved = approve_baseline(
        artifacts,
        route_id="home",
        source_png=src,
        comparison_id="cmp-1",
        label="Home",
    )
    assert approved["hasBaseline"] is True
    assert approved["status"] == "approved"
    assert (artifacts / "baselines" / "home" / "baseline.png").is_file()

    items = list_baselines(artifacts)
    assert len(items) == 1
    assert items[0]["routeId"] == "home"

    rejected = reject_baseline(artifacts, route_id="home", notes="layout drift", remove_image=False)
    assert rejected["status"] == "rejected"
    assert rejected["hasBaseline"] is True  # image kept

    reject_baseline(artifacts, route_id="home", remove_image=True)
    again = get_baseline(artifacts, "home")
    assert again is not None
    assert again["hasBaseline"] is False

    assert delete_baseline(artifacts, "home") is True
    assert get_baseline(artifacts, "home") is None


def test_find_comparison_actual(tmp_path: Path) -> None:
    artifacts = tmp_path / "visual"
    folder = artifacts / "cmp-abc"
    folder.mkdir(parents=True)
    (folder / "actual.png").write_bytes(PNG_1X1)
    path = find_comparison_actual(artifacts, "cmp-abc")
    assert path.name == "actual.png"


def test_api_approve_via_path(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    mockups = project / "mockups"
    mockups.mkdir()
    img = mockups / "home.png"
    img.write_bytes(PNG_1X1)
    engine = VisualEngine(project, project_id="proj")
    code, payload = visual_api.handle_approve_baseline(
        engine,
        {"routeId": "landing", "path": "mockups/home.png", "label": "Landing"},
    )
    assert code == 200
    assert payload["baseline"]["routeId"] == "landing"
    code2, listed = visual_api.handle_list_baselines(engine)
    assert code2 == 200
    assert any(b["routeId"] == "landing" for b in listed["baselines"])
