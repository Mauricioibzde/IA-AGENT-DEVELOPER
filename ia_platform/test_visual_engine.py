"""Phase 1 Visual Engine tests (no Chromium required for image-vs-image)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from ia_platform.visual_engine.models import CompareRequest, Side
from ia_platform.visual_engine.security import validate_compare_url
from ia_platform.visual_engine.service import VisualEngine


def _png(width: int, height: int, rgb=(255, 0, 0)) -> bytes:
    """Minimal solid-color PNG without Pillow."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def test_validate_url_allows_forge_preview_ports() -> None:
    validate_compare_url("http://127.0.0.1:9205/")
    validate_compare_url("http://localhost:8787/preview/demo/index.html")
    with pytest.raises(ValueError):
        validate_compare_url("http://127.0.0.1:9999/")
    with pytest.raises(ValueError):
        validate_compare_url("file:///etc/passwd")


def test_compare_images_via_bridge(tmp_path: Path) -> None:
    engine = VisualEngine(tmp_path)
    if not engine.available():
        pytest.skip("Node.js not available")
    (tmp_path / "a.png").write_bytes(_png(32, 24, (10, 20, 30)))
    (tmp_path / "b.png").write_bytes(_png(32, 24, (10, 20, 30)))
    report = engine.compare(
        CompareRequest(
            source=Side(type="image", value="a.png"),
            target=Side(type="image", value="b.png"),
            options={"inline": True},
        )
    )
    assert report.status == "completed"
    assert report.similarity == 1.0


def test_compare_images_writes_artifacts(tmp_path: Path) -> None:
    engine = VisualEngine(tmp_path)
    if not engine.available():
        pytest.skip("Node.js not available")
    (tmp_path / "a.png").write_bytes(_png(40, 30, (255, 0, 0)))
    (tmp_path / "b.png").write_bytes(_png(40, 30, (0, 0, 255)))
    report = engine.compare(
        CompareRequest(
            source=Side(type="image", value="a.png"),
            target=Side(type="image", value="b.png"),
            comparison_id="phase1-diff",
        )
    )
    assert report.mode == "image-vs-image"
    assert report.similarity is not None and report.similarity < 1.0
    art = Path(report.artifacts.get("directory") or "")
    assert art.is_dir()
    assert (art / "report.json").is_file()
    assert (art / "diff.png").is_file()
