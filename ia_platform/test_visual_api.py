"""Phase 2 Visual Engine HTTP routes."""

from __future__ import annotations

import importlib.util
import json
import struct
import threading
import zlib
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_SERVER_PATH = Path(__file__).resolve().parent / "server.py"
_spec = importlib.util.spec_from_file_location("ia_platform_server_visual", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_mod)
PlatformHandler = _mod.PlatformHandler
PROJECTS_ROOT = _mod.PROJECTS_ROOT


def _png(width: int, height: int, rgb=(255, 0, 0)) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def platform_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(_mod, "PROJECTS_ROOT", tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), PlatformHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _create_project(platform_url: str, name: str = "visual-demo") -> str:
    import urllib.request

    req = urllib.request.Request(
        f"{platform_url}/api/projects",
        data=json.dumps({"name": name, "template": "blank"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    return data.get("id") or data.get("project", {}).get("id") or name


def test_visual_status_and_image_compare(platform_url: str, tmp_path: Path) -> None:
    import urllib.request

    from ia_platform.visual_engine.bridge import node_available

    if not node_available():
        pytest.skip("Node not available")

    pid = _create_project(platform_url)
    proj = tmp_path / pid
    (proj / "a.png").write_bytes(_png(24, 24, (1, 2, 3)))
    (proj / "b.png").write_bytes(_png(24, 24, (1, 2, 3)))

    with urllib.request.urlopen(f"{platform_url}/api/projects/{pid}/visual/status", timeout=30) as resp:
        status = json.loads(resp.read().decode())
    assert status.get("node") is True

    body = json.dumps(
        {
            "source": {"type": "image", "value": "a.png"},
            "target": {"type": "image", "value": "b.png"},
            "comparisonId": "api-same",
        }
    ).encode()
    req = urllib.request.Request(
        f"{platform_url}/api/projects/{pid}/visual/compare",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    assert data["ok"] is True
    assert data["report"]["similarity"] == 1.0

    with urllib.request.urlopen(f"{platform_url}/api/projects/{pid}/visual/comparisons", timeout=10) as resp:
        hist = json.loads(resp.read().decode())
    assert any(c.get("comparisonId") == "api-same" for c in hist.get("comparisons") or [])

    with urllib.request.urlopen(
        f"{platform_url}/api/projects/{pid}/visual/comparisons/api-same/diff.png", timeout=10
    ) as resp:
        assert resp.headers.get_content_type() in {"image/png", "application/octet-stream"}
        assert len(resp.read()) > 20


def test_preview_url_resolver(tmp_path: Path) -> None:
    from ia_platform.visual_engine.service import VisualEngine

    eng = VisualEngine(tmp_path, project_id="demo", forge_port=8787)
    url = eng.resolve_preview_url(host_header="127.0.0.1:8787", mode="static")
    assert url.endswith("/preview/demo/index.html")


def test_validate_security_helpers() -> None:
    from ia_platform.visual_engine.api import parse_side

    side = parse_side({"type": "image", "value": "x.png"})
    assert side.type == "image"
    side2 = parse_side("https://example.com")
    assert side2.type == "url"
