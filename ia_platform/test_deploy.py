"""Tests for deploy helpers."""

from __future__ import annotations

import json
from pathlib import Path

from ia_platform.deploy import ensure_vercel_config, manual_deploy_steps


def test_ensure_vercel_static(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    path = ensure_vercel_config(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data.get("cleanUrls") is True


def test_ensure_vercel_vite(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"build": "vite build"}, "devDependencies": {"vite": "^5.0.0"}}),
        encoding="utf-8",
    )
    path = ensure_vercel_config(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["buildCommand"] == "npm run build"
    assert data["outputDirectory"] == "dist"


def test_manual_steps() -> None:
    steps = manual_deploy_steps("meu-app")
    assert any("vercel" in s.lower() for s in steps)
