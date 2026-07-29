"""Tests for shared project templates."""

from __future__ import annotations

import json

from ia_platform.project_templates import get_template_files, react_vite_files


def test_react_vite_files_uses_project_name() -> None:
    files = react_vite_files("Meu App!")
    pkg = json.loads(files["package.json"])
    assert pkg["name"] == "meu-app"
    assert "dev" in pkg["scripts"]
    assert "127.0.0.1" in files["vite.config.js"]
    assert "PORT" in files["vite.config.js"]
    assert "Meu App!" in files["index.html"]


def test_get_template_files_react_is_dynamic() -> None:
    a = get_template_files("react", "alpha-app")
    b = get_template_files("react", "beta-app")
    assert json.loads(a["package.json"])["name"] == "alpha-app"
    assert json.loads(b["package.json"])["name"] == "beta-app"


def test_get_template_files_landing() -> None:
    files = get_template_files("landing", "x")
    assert "index.html" in files
    assert files["index.html"]
