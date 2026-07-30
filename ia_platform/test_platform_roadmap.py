"""Tests for platform roadmap features (projects, deploy preflight, search, index cache)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ia_platform.deploy import deploy_preflight
from ia_platform.project_ops import archive_project, duplicate_project, list_projects, rename_project
from ia_platform.project_templates import get_template_files, react_vite_files
from local_agent.config import AgentConfig
from local_agent.project_index import ProjectIndex
from local_agent.tools.search import search_relevant


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in name)[:64] or "project"


def test_project_ops_rename_duplicate_archive(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    src = root / "alpha"
    src.mkdir()
    (src / "README.md").write_text("# a\n", encoding="utf-8")

    renamed = rename_project(root, "alpha", "beta", _safe)
    assert renamed["id"] == "beta"
    assert (root / "beta" / "README.md").is_file()

    dup = duplicate_project(root, "beta", _safe)
    assert (root / dup["id"] / "README.md").is_file()

    archived = archive_project(root, "beta")
    assert archived["archived"] is True
    assert not (root / "beta").exists()
    assert (root / ".archive" / archived["id"]).is_dir()

    listed = list_projects(root, query="copy")
    assert any(p["id"] == dup["id"] for p in listed)
    assert all(not p.get("archived") for p in listed)


def test_deploy_preflight_checklist(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    data = deploy_preflight(tmp_path)
    assert "requirements" in data
    ids = {r["id"] for r in data["requirements"]}
    assert {"token", "node", "app"} <= ids
    assert data["has_index_html"] is True


def test_react_template_has_gitignore() -> None:
    files = react_vite_files("Cool App")
    assert "node_modules" in files[".gitignore"]
    assert "Cool App" in files["README.md"]
    assert json.loads(files["package.json"])["name"] == "cool-app"


def test_landing_template_uses_project_name() -> None:
    files = get_template_files("landing", "MinhaLanding")
    assert "MinhaLanding" in files["index.html"]


def test_search_relevant_tool(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "AuthService.js").write_text(
        "export function login(){ return true }\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# docs\n", encoding="utf-8")
    cfg = AgentConfig.from_args(tmp_path, no_memory=True, no_git=True)
    result = search_relevant({"query": "login auth"}, workspace=str(tmp_path), config=cfg)
    assert result.ok
    paths = [m["path"] for m in result.data["matches"]]
    assert any("AuthService" in p for p in paths)


def test_project_index_cache(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    index = ProjectIndex(tmp_path)
    index.build(use_cache=True)
    cache = tmp_path / ".agent" / "index.json"
    assert cache.is_file()
    index2 = ProjectIndex(tmp_path)
    assert index2.build(use_cache=True) is index2
    assert any(f.path == "main.py" for f in index2.files)
