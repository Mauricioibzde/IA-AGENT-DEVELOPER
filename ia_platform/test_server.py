"""Platform server smoke tests (no live Ollama required for routing)."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_SERVER_PATH = Path(__file__).resolve().parent / "server.py"
_spec = importlib.util.spec_from_file_location("ia_platform_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_mod)
PlatformHandler = _mod.PlatformHandler
DEFAULT_WORKSPACE = _mod.DEFAULT_WORKSPACE
PROJECTS_ROOT = _mod.PROJECTS_ROOT


@pytest.fixture
def platform_url() -> str:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), PlatformHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    yield url
    httpd.shutdown()


def test_health_endpoint(platform_url: str) -> None:
    req = urllib.request.Request(f"{platform_url}/api/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert data["agent"] is True
    assert "ollama" in data


def test_index_html(platform_url: str) -> None:
    with urllib.request.urlopen(f"{platform_url}/", timeout=5) as resp:
        html = resp.read().decode("utf-8")
    assert "Forge" in html
    assert "/static/app.css" in html
    assert "/static/app.js" in html


def test_static_assets(platform_url: str) -> None:
    for asset in ("/static/app.css", "/static/app.js"):
        with urllib.request.urlopen(f"{platform_url}{asset}", timeout=5) as resp:
            body = resp.read().decode("utf-8")
        assert len(body) > 50


def test_run_requires_prompt(platform_url: str) -> None:
    req = urllib.request.Request(
        f"{platform_url}/api/run",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=5)
    assert exc.value.code == 400


def test_default_workspace_exists() -> None:
    DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)
    assert DEFAULT_WORKSPACE.is_dir()


def test_list_projects_empty(platform_url: str) -> None:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{platform_url}/api/projects", timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert "projects" in data
    assert isinstance(data["projects"], list)


def test_create_project_with_template(platform_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path / "projects")
    name = "test-landing"
    req = urllib.request.Request(
        f"{platform_url}/api/projects",
        data=json.dumps({"name": name, "template": "landing"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert resp.status == 201
    assert data["id"] == name
    project_dir = tmp_path / "projects" / name
    assert (project_dir / "index.html").is_file()
    assert (project_dir / "style.css").is_file()

    files_req = urllib.request.Request(f"{platform_url}/api/projects/{name}/files?recursive=1")
    with urllib.request.urlopen(files_req, timeout=5) as resp:
        files_data = json.loads(resp.read().decode())
    paths = {f["path"] for f in files_data["files"]}
    assert "index.html" in paths

    preview = urllib.request.urlopen(f"{platform_url}/preview/{name}/index.html", timeout=5)
    assert preview.status == 200
    assert b"<!DOCTYPE html>" in preview.read()


def test_read_project_file(platform_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path / "projects")
    project_dir = tmp_path / "projects" / "demo"
    project_dir.mkdir(parents=True)
    (project_dir / "hello.txt").write_text("ola", encoding="utf-8")

    req = urllib.request.Request(f"{platform_url}/api/projects/demo/file?path=hello.txt")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert data["content"] == "ola"


def test_chat_persistence(platform_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path / "projects")
    project_dir = tmp_path / "projects" / "chat-demo"
    project_dir.mkdir(parents=True)

    post = urllib.request.Request(
        f"{platform_url}/api/projects/chat-demo/chat",
        data=json.dumps({"role": "user", "text": "crie um site"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(post, timeout=5) as resp:
        created = json.loads(resp.read().decode())
    assert created["ok"] is True
    assert len(created["messages"]) == 1

    with urllib.request.urlopen(f"{platform_url}/api/projects/chat-demo/chat", timeout=5) as resp:
        loaded = json.loads(resp.read().decode())
    assert loaded["messages"][0]["text"] == "crie um site"


def test_dev_status(platform_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path / "projects")
    project_dir = tmp_path / "projects" / "vite-app"
    project_dir.mkdir(parents=True)
    (project_dir / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite"}}),
        encoding="utf-8",
    )
    with urllib.request.urlopen(f"{platform_url}/api/projects/vite-app/dev/status", timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert data["has_dev_script"] is True
    assert data["script"] == "dev"
    assert data["running"] is False


def test_deploy_without_token(platform_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path / "projects")
    project_dir = tmp_path / "projects" / "static-site"
    project_dir.mkdir(parents=True)
    (project_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    req = urllib.request.Request(
        f"{platform_url}/api/projects/static-site/deploy",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert data["ok"] is False
    assert data.get("manual") is True
    assert (project_dir / "vercel.json").is_file()


def test_create_react_template(platform_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path / "projects")
    req = urllib.request.Request(
        f"{platform_url}/api/projects",
        data=json.dumps({"name": "my-react", "template": "react"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert data["template"] == "react"
    project_dir = tmp_path / "projects" / "my-react"
    assert (project_dir / "package.json").is_file()
    assert (project_dir / "vite.config.js").is_file()
    assert (project_dir / "src" / "App.jsx").is_file()
    pkg = json.loads((project_dir / "package.json").read_text(encoding="utf-8"))
    assert "dev" in pkg.get("scripts", {})


def test_run_stream_emits_sse(platform_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path / "projects")
    project_dir = tmp_path / "projects" / "stream-demo"
    project_dir.mkdir(parents=True)

    from local_agent.agent import CodingAgent
    from local_agent.models import AgentReport, FinalStatus

    def fake_run(self, prompt: str) -> AgentReport:
        if self.event_sink:
            self.event_sink({"type": "plan", "summary": "demo plan", "task_count": 1})
        return AgentReport(status=FinalStatus.SUCCESS, goal=prompt, summary="stream ok")

    monkeypatch.setattr(CodingAgent, "run", fake_run)

    req = urllib.request.Request(
        f"{platform_url}/api/run/stream",
        data=json.dumps({"prompt": "teste", "workspace": "projects/stream-demo"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
    assert "text/event-stream" in resp.headers.get("Content-Type", "")
    assert '"type": "plan"' in body.replace(" ", "") or '"type":"plan"' in body.replace(" ", "")
    assert "done" in body
    assert "stream ok" in body


def test_hardware_endpoint(platform_url: str) -> None:
    with urllib.request.urlopen(f"{platform_url}/api/system/hardware", timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert data["hardware"]["ram_total_gb"] > 0
    assert data["hardware"]["tier"]


def test_model_recommendations_endpoint(platform_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMgr:
        def list_names(self):
            return ["qwen2.5-coder:7b"]

    monkeypatch.setattr(_mod, "OllamaModelManager", lambda host: FakeMgr())
    with urllib.request.urlopen(f"{platform_url}/api/models/recommendations", timeout=5) as resp:
        data = json.loads(resp.read().decode())
    assert data["primary"]["ollama_name"]
    assert len(data["catalog"]) >= 5
    assert any(m.get("installed") for m in data["catalog"])


def test_model_pull_stream(platform_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMgr:
        def pull(self, model, on_event=None, timeout=3600):
            if on_event:
                on_event({"type": "progress", "model": model, "status": "pulling", "percent": 50})
            return {"ok": True, "model": model}

    monkeypatch.setattr(_mod, "OllamaModelManager", lambda host: FakeMgr())
    req = urllib.request.Request(
        f"{platform_url}/api/models/pull/stream",
        data=json.dumps({"model": "qwen2.5-coder:7b"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
    assert "done" in body
    assert "qwen2.5-coder:7b" in body
