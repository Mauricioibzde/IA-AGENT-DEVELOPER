"""Deterministic color palette sampling from mockup images (ffmpeg, no Pillow)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _ffmpeg_bin() -> Optional[str]:
    return shutil.which("ffmpeg")


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _color_dist(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def _merge_similar(
    counts: Counter,
    *,
    threshold: int = 48,
    max_colors: int = 8,
) -> List[Tuple[Tuple[int, int, int], int]]:
    """Greedy merge of near-duplicate RGB buckets, keeping dominant colors."""
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    merged: List[Tuple[Tuple[int, int, int], int]] = []
    for color, count in ranked:
        placed = False
        for idx, (existing, existing_count) in enumerate(merged):
            if _color_dist(color, existing) <= threshold:
                # Keep the more frequent representative; sum counts.
                total = existing_count + count
                rep = existing if existing_count >= count else color
                merged[idx] = (rep, total)
                placed = True
                break
        if not placed:
            merged.append((color, count))
        if len(merged) >= max_colors * 3:
            break
    merged.sort(key=lambda item: item[1], reverse=True)
    return merged[:max_colors]


def sample_palette(
    image_path: Path,
    *,
    max_colors: int = 8,
    sample_edge: int = 96,
) -> Dict[str, Any]:
    """Sample dominant colors from an image via ffmpeg → rgb24 histogram.

    Returns {"ok": bool, "colors": [{"hex": "#rrggbb", "pct": 0.42}, ...], "error"?}
    """
    path = Path(image_path)
    if not path.is_file():
        return {"ok": False, "colors": [], "error": f"image not found: {path}"}

    ffmpeg = _ffmpeg_bin()
    if not ffmpeg:
        return {"ok": False, "colors": [], "error": "ffmpeg unavailable"}

    with tempfile.TemporaryDirectory(prefix="forge-palette-") as tmp:
        raw_path = Path(tmp) / "sample.rgb"
        # Scale down for speed; force even dimensions for some codecs.
        edge = max(16, int(sample_edge))
        vf = f"scale={edge}:{edge}:force_original_aspect_ratio=decrease,format=rgb24"
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(path),
            "-vf",
            vf,
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            str(raw_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=45)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            return {"ok": False, "colors": [], "error": f"palette sample failed: {exc}"}

        data = raw_path.read_bytes()
        if len(data) < 3:
            return {"ok": False, "colors": [], "error": "empty rgb sample"}

        counts: Counter = Counter()
        for i in range(0, len(data) - 2, 3):
            counts[(data[i], data[i + 1], data[i + 2])] += 1

        total = sum(counts.values()) or 1
        merged = _merge_similar(counts, max_colors=max_colors)
        colors = [
            {
                "hex": _rgb_to_hex(*rgb),
                "pct": round(count / total, 4),
                "rgb": list(rgb),
            }
            for rgb, count in merged
            if count / total >= 0.01
        ]
        return {"ok": True, "colors": colors, "samples": total}


def format_palette_for_goal(colors: List[Dict[str, Any]], *, limit: int = 8) -> str:
    """Dense palette block for CodingAgent goals."""
    if not colors:
        return ""
    lines = ["## Paleta amostrada do mockup (determinística — use estes hex)"]
    for item in colors[:limit]:
        hex_color = str(item.get("hex") or "").strip()
        if not hex_color:
            continue
        pct = item.get("pct")
        pct_bit = f" (~{float(pct) * 100:.0f}%)" if isinstance(pct, (int, float)) else ""
        lines.append(f"- {hex_color}{pct_bit}")
    if len(lines) <= 1:
        return ""
    lines.append(
        "Aplique esses tons em CSS variables / fundos / textos / accents; "
        "não substitua por cinzas genéricos."
    )
    return "\n".join(lines)


def resolve_mockup_path(workspace: Path, mockup_rel_or_abs: str) -> Optional[Path]:
    """Resolve a mockup path inside the workspace, or None if invalid."""
    workspace = Path(workspace).resolve()
    raw = str(mockup_rel_or_abs or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (workspace / path).resolve()
    try:
        path.relative_to(workspace)
    except ValueError:
        return None
    return path if path.is_file() else None
