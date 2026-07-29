"""Model recommendation tests."""

from __future__ import annotations

from ia_platform.model_catalog import MODEL_CATALOG, recommend_models, resolve_model_for_run


def test_recommend_medium_hardware() -> None:
    hw = {
        "tier": "medium",
        "effective_memory_gb": 10,
        "ram_total_gb": 16,
        "ram_available_gb": 12,
        "has_gpu": True,
        "vram_total_gb": 8,
        "vram_free_gb": 7,
        "cpu_cores": 8,
        "gpus": [],
    }
    rec = recommend_models(hw, installed=["llama3.2:3b"])
    assert rec["primary"]["ollama_name"]
    assert rec["primary"]["fits"] is True
    assert any(item["ollama_name"] == "qwen2.5-coder:7b" for item in rec["catalog"])


def test_recommend_low_hardware_prefers_small_models() -> None:
    hw = {
        "tier": "low",
        "effective_memory_gb": 5,
        "ram_total_gb": 8,
        "ram_available_gb": 5,
        "has_gpu": False,
        "vram_total_gb": 0,
        "vram_free_gb": 0,
        "cpu_cores": 4,
        "gpus": [],
    }
    rec = recommend_models(hw, installed=[])
    primary = rec["primary"]
    assert primary["params_b"] <= 7
    assert primary["fits"] is True


def test_catalog_not_empty() -> None:
    assert len(MODEL_CATALOG) >= 5


def test_resolve_model_for_run_prefers_installed() -> None:
    hw = {"tier": "medium", "effective_memory_gb": 10, "has_gpu": False, "ram_total_gb": 16, "ram_available_gb": 12, "vram_total_gb": 0, "vram_free_gb": 0, "cpu_cores": 8, "gpus": []}
    model = resolve_model_for_run("", ["deepseek-coder:6.7b"], hw)
    assert "deepseek" in model

