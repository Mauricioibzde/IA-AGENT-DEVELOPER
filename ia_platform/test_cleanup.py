"""Phase 8 cleanup + telemetry unit tests."""

from __future__ import annotations

import time
from pathlib import Path

from ia_platform.visual_engine.cleanup import cleanup_artifacts, cleanup_stats, list_comparison_dirs
from ia_platform.visual_engine.telemetry import record, snapshot


def test_cleanup_skips_baselines_and_prunes_old(tmp_path: Path) -> None:
    root = tmp_path / "visual"
    old = root / "old-cmp"
    old.mkdir(parents=True)
    (old / "report.json").write_text("{}", encoding="utf-8")
    # Age the directory
    old_mtime = time.time() - (10 * 24 * 3600)
    Path(old).touch()
    import os

    os.utime(old, (old_mtime, old_mtime))

    fresh = root / "fresh-cmp"
    fresh.mkdir()
    (fresh / "report.json").write_text("{}", encoding="utf-8")

    base = root / "baselines" / "home"
    base.mkdir(parents=True)
    (base / "baseline.png").write_bytes(b"x")

    corr = root / "corrections"
    corr.mkdir()
    (corr / "j1.json").write_text("{}", encoding="utf-8")

    result = cleanup_artifacts(root, max_age_sec=7 * 24 * 3600, max_comparisons=80)
    assert result["deleted"] >= 1
    assert "old-cmp" in result["deletedIds"]
    assert fresh.is_dir()
    assert base.is_dir()  # protected
    assert corr.is_dir()  # protected


def test_cleanup_by_count(tmp_path: Path) -> None:
    root = tmp_path / "visual"
    for i in range(5):
        d = root / f"c{i}"
        d.mkdir(parents=True)
        (d / "report.json").write_text("{}", encoding="utf-8")
        # Stagger mtimes so ordering is stable
        import os

        os.utime(d, (time.time() - (5 - i), time.time() - (5 - i)))
    result = cleanup_artifacts(root, max_age_sec=0, max_comparisons=2)
    # max_age_sec=0 means everything is "too old" if we check age > 0...
    # Our code: if max_age_sec > 0 and age > max_age_sec — so 0 disables age.
    assert result["kept"] == 2
    assert result["deleted"] == 3
    assert len(list_comparison_dirs(root)) == 2


def test_cleanup_stats_and_telemetry(tmp_path: Path) -> None:
    root = tmp_path / "visual"
    (root / "a").mkdir(parents=True)
    stats = cleanup_stats(root)
    assert stats["comparisons"] == 1
    record("compare", duration_ms=12, ok=True)
    snap = snapshot()
    assert snap["compares"] >= 1
    assert snap["lastDurationMs"] == 12
