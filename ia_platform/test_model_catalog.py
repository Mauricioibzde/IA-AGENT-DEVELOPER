"""Model recommendation tests."""

from __future__ import annotations

from ia_platform.model_catalog import (
    MODEL_CATALOG,
    recommend_models,
    recommend_setup_model,
    resolve_model_for_chat,
    resolve_model_for_run,
    resolve_models_for_run,
)


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


def test_recommend_setup_model_cpu_prefers_small_coder() -> None:
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
    model = recommend_setup_model(hw, installed=[])
    assert "deepseek-coder:6.7b" not in model
    assert "coder" in model or "qwen" in model


def test_recommend_setup_model_gpu_uses_primary() -> None:
    hw = {
        "tier": "medium",
        "effective_memory_gb": 10,
        "ram_total_gb": 16,
        "ram_available_gb": 12,
        "has_gpu": True,
        "vram_total_gb": 8,
        "vram_free_gb": 7,
        "cpu_cores": 8,
        "gpus": [{"name": "RTX 3060"}],
    }
    primary = recommend_models(hw, installed=[])["primary"]["ollama_name"]
    assert recommend_setup_model(hw, installed=[]) == primary


def test_recommend_setup_model_prefers_installed_cpu() -> None:
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
    model = recommend_setup_model(hw, installed=["qwen2.5-coder:1.5b"])
    assert model == "qwen2.5-coder:1.5b"


def test_recommend_setup_model_returns_exact_installed_variant() -> None:
    hw = {
        "tier": "minimal",
        "effective_memory_gb": 4,
        "ram_total_gb": 8,
        "ram_available_gb": 4,
        "has_gpu": False,
        "vram_total_gb": 0,
        "vram_free_gb": 0,
        "cpu_cores": 4,
        "gpus": [],
    }
    model = recommend_setup_model(hw, installed=["qwen2.5-coder:1.5b-base"])
    assert model == "qwen2.5-coder:1.5b-base"


def test_recommend_setup_model_prefers_exact_coder_over_base_variant() -> None:
    hw = {
        "tier": "minimal",
        "effective_memory_gb": 1.2,
        "ram_total_gb": 16,
        "ram_available_gb": 2,
        "has_gpu": False,
        "vram_total_gb": 0,
        "vram_free_gb": 0,
        "cpu_cores": 10,
        "gpus": [],
    }
    installed = ["qwen2.5-coder:1.5b-base", "qwen2.5-coder:7b"]
    model = recommend_setup_model(hw, installed=installed)
    assert model == "qwen2.5-coder:7b"


def test_catalog_not_empty() -> None:
    assert len(MODEL_CATALOG) >= 5


def test_resolve_model_for_run_prefers_installed() -> None:
    hw = {"tier": "medium", "effective_memory_gb": 10, "has_gpu": False, "ram_total_gb": 16, "ram_available_gb": 12, "vram_total_gb": 0, "vram_free_gb": 0, "cpu_cores": 8, "gpus": []}
    model = resolve_model_for_run("", ["deepseek-coder:6.7b"], hw)
    assert "deepseek" in model


def test_resolve_model_for_run_returns_exact_installed_variant() -> None:
    hw = {"tier": "minimal", "effective_memory_gb": 4, "has_gpu": False, "ram_total_gb": 8, "ram_available_gb": 4, "vram_total_gb": 0, "vram_free_gb": 0, "cpu_cores": 4, "gpus": []}
    model = resolve_model_for_run("", ["qwen2.5-coder:1.5b-base"], hw)
    assert model == "qwen2.5-coder:1.5b-base"


def test_resolve_models_uses_light_planner_on_low_tier() -> None:
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
    installed = ["qwen2.5-coder:7b", "qwen2.5-coder:1.5b"]
    models = resolve_models_for_run("", installed, hw)
    assert models["planner"] == "qwen2.5-coder:1.5b"
    assert models["reflection"] == "qwen2.5-coder:1.5b"
    assert models["coder"] in installed


def test_resolve_model_for_chat_prefers_conversational() -> None:
    hw = {"tier": "medium", "effective_memory_gb": 10, "has_gpu": False}
    installed = ["qwen2.5-coder:1.5b-base", "llama3.2:3b", "qwen2.5-coder:7b"]
    model = resolve_model_for_chat(None, installed, hw)
    assert model == "llama3.2:3b"


def test_resolve_model_for_chat_avoids_base_when_auto() -> None:
    hw = {"tier": "minimal", "effective_memory_gb": 4, "has_gpu": False}
    installed = ["qwen2.5-coder:1.5b-base", "mistral:7b"]
    model = resolve_model_for_chat("", installed, hw)
    assert model == "mistral:7b"

