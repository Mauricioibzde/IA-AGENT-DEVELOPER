"""Tests for dev server detection."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from ia_platform.dev_server import DevServerError, DevServerManager


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
    assert status["last_error"] is None


def test_npm_install_failure_surfaces_stderr(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8")
    mgr = DevServerManager()
    with patch.object(mgr, "_npm_available", return_value=True):
        with patch(
            "ia_platform.dev_server.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "npm", stderr="npm ERR! broken deps"),
        ):
            with pytest.raises(DevServerError) as exc:
                mgr._ensure_dependencies(tmp_path)
    assert "npm install falhou" in str(exc.value)
    assert "broken deps" in exc.value.stderr
