"""Tests for dev server detection."""

from __future__ import annotations

import json
from pathlib import Path

from ia_platform.dev_server import DevServerManager


def test_detect_dev_script() -> None:
    mgr = DevServerManager()
    assert mgr.detect_dev_script(Path("/nonexistent")) is None


def test_detect_dev_script_found(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite", "build": "vite build"}}),
        encoding="utf-8",
    )
    mgr = DevServerManager()
    assert mgr.detect_dev_script(tmp_path) == "dev"


def test_status_no_npm_project(tmp_path: Path) -> None:
    mgr = DevServerManager()
    status = mgr.status("demo", tmp_path)
    assert status["has_dev_script"] is False
    assert status["running"] is False
