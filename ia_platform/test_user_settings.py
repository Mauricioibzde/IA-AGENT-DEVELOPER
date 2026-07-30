"""Tests for user hardware profile settings."""

from __future__ import annotations

from pathlib import Path

from ia_platform.hardware import apply_user_hardware_profile
from ia_platform.model_catalog import recommend_models, resolve_model_for_chat
from ia_platform.user_settings import HARDWARE_PRESETS, load_settings, save_settings


def test_save_and_load_manual_preset(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    saved = save_settings({"hardware_preset": "desktop-40-gpu8"}, path=path)
    assert saved["hardware_mode"] == "manual"
    assert saved["hardware_profile"]["ram_total_gb"] == 40
    assert saved["hardware_profile"]["vram_total_gb"] == 8
    assert saved["hardware_profile"]["has_gpu"] is True
    loaded = load_settings(path)
    assert loaded["hardware_preset"] == "desktop-40-gpu8"


def test_apply_user_profile_changes_recommendations(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    save_settings({"hardware_preset": "desktop-40-gpu8"}, path=path)
    settings = load_settings(path)
    detected = {
        "os": "Linux",
        "machine": "x86_64",
        "cpu_cores": 4,
        "ram_total_gb": 16,
        "ram_available_gb": 15,
        "has_gpu": False,
        "gpus": [],
        "vram_total_gb": 0,
        "vram_free_gb": 0,
        "tier": "medium",
        "effective_memory_gb": 9.8,
        "hostname": "cursor",
        "source": "container",
        "fingerprint": "abc",
        "detected_at": 1,
        "scope": "server",
        "note": "server",
    }
    effective = apply_user_hardware_profile(detected, settings)
    assert effective["profile_mode"] == "manual"
    assert effective["ram_total_gb"] == 40
    assert effective["vram_total_gb"] == 8
    assert effective["has_gpu"] is True

    installed = ["qwen2.5-coder:32b", "deepseek-coder:6.7b"]
    weak = recommend_models(detected, installed)
    strong = recommend_models(effective, installed)
    by_weak = {i["ollama_name"]: i for i in weak["catalog"]}
    by_strong = {i["ollama_name"]: i for i in strong["catalog"]}
    assert by_weak["qwen2.5-coder:32b"]["fits"] is False
    assert by_strong["qwen2.5-coder:32b"]["fits"] is True
    assert resolve_model_for_chat(None, installed, effective) in {
        "qwen2.5-coder:32b",
        "deepseek-coder:6.7b",
    }


def test_presets_include_desktop_40() -> None:
    assert "desktop-40-gpu8" in HARDWARE_PRESETS
