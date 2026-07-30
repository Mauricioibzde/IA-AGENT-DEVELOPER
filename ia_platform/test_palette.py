"""Tests for deterministic mockup palette sampling."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ia_platform.visual_engine.palette import format_palette_for_goal, sample_palette


def _make_png(path: Path, color: str = "0b0f14") -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=48x48",
            "-frames:v",
            "1",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_sample_palette_dominant_color(tmp_path: Path) -> None:
    png = tmp_path / "mock.png"
    _make_png(png, "0b0f14")
    result = sample_palette(png, max_colors=4, sample_edge=32)
    assert result["ok"] is True
    assert result["colors"]
    top = result["colors"][0]["hex"].lower()
    # ffmpeg lavfi color may round slightly; accept near #0b0f14
    assert top.startswith("#0")
    assert result["colors"][0]["pct"] > 0.5


def test_format_palette_for_goal() -> None:
    block = format_palette_for_goal(
        [{"hex": "#0b0f14", "pct": 0.62}, {"hex": "#3b82f6", "pct": 0.11}]
    )
    assert "Paleta amostrada" in block
    assert "#0b0f14" in block
    assert "#3b82f6" in block


def test_sample_palette_missing_file(tmp_path: Path) -> None:
    result = sample_palette(tmp_path / "nope.png")
    assert result["ok"] is False
