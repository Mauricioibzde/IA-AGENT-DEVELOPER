"""Hardware detection tests."""

from __future__ import annotations

from ia_platform.hardware import _compute_tier, detect_hardware


def test_detect_hardware_returns_profile() -> None:
    hw = detect_hardware()
    assert hw["ram_total_gb"] > 0
    assert hw["cpu_cores"] >= 1
    assert hw["tier"] in {"minimal", "low", "medium", "high", "ultra"}
    assert "effective_memory_gb" in hw


def test_compute_tier_ultra() -> None:
    assert _compute_tier(ram_gb=64, vram_gb=24, cpu_cores=16) == "ultra"


def test_compute_tier_minimal() -> None:
    assert _compute_tier(ram_gb=4, vram_gb=0, cpu_cores=2) == "minimal"
