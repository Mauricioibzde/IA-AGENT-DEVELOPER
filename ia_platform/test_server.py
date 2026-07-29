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
    assert "IA Agent Developer" in html


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
