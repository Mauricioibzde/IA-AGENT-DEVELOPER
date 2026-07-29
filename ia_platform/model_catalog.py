"""Curated Ollama model catalog and hardware-aware recommendations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ModelEntry:
    id: str
    name: str
    ollama_name: str
    params_b: float
    ram_gb: float
    vram_gb: float
    size_gb: float
    tags: tuple[str, ...]
    description: str
    tier: str  # minimal | low | medium | high | ultra

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        return data


MODEL_CATALOG: List[ModelEntry] = [
    ModelEntry(
        id="qwen2.5-coder-1.5b",
        name="Qwen2.5 Coder 1.5B",
        ollama_name="qwen2.5-coder:1.5b",
        params_b=1.5,
        ram_gb=4,
        vram_gb=3,
        size_gb=1.0,
        tags=("coder", "fast", "low-end"),
        description="Muito leve. Bom para PCs fracos e testes rápidos.",
        tier="minimal",
    ),
    ModelEntry(
        id="qwen2.5-coder-3b",
        name="Qwen2.5 Coder 3B",
        ollama_name="qwen2.5-coder:3b",
        params_b=3,
        ram_gb=6,
        vram_gb=4,
        size_gb=2.0,
        tags=("coder", "fast"),
        description="Equilíbrio leve para notebooks com 8 GB RAM.",
        tier="low",
    ),
    ModelEntry(
        id="deepseek-coder-6.7b",
        name="DeepSeek Coder 6.7B",
        ollama_name="deepseek-coder:6.7b",
        params_b=6.7,
        ram_gb=8,
        vram_gb=6,
        size_gb=3.8,
        tags=("coder", "recommended"),
        description="Forte em código. Recomendado com GPU de 6 GB+.",
        tier="medium",
    ),
    ModelEntry(
        id="qwen2.5-coder-7b",
        name="Qwen2.5 Coder 7B",
        ollama_name="qwen2.5-coder:7b",
        params_b=7,
        ram_gb=8,
        vram_gb=6,
        size_gb=4.7,
        tags=("coder", "recommended", "default"),
        description="Melhor custo/benefício para geração de apps local.",
        tier="medium",
    ),
    ModelEntry(
        id="codellama-7b",
        name="Code Llama 7B",
        ollama_name="codellama:7b",
        params_b=7,
        ram_gb=8,
        vram_gb=6,
        size_gb=3.8,
        tags=("coder",),
        description="Clássico para código. Alternativa ao Qwen 7B.",
        tier="medium",
    ),
    ModelEntry(
        id="qwen2.5-coder-14b",
        name="Qwen2.5 Coder 14B",
        ollama_name="qwen2.5-coder:14b",
        params_b=14,
        ram_gb=16,
        vram_gb=10,
        size_gb=9.0,
        tags=("coder", "quality"),
        description="Qualidade superior. Ideal com 16 GB RAM ou GPU 10 GB+.",
        tier="high",
    ),
    ModelEntry(
        id="deepseek-coder-v2-16b",
        name="DeepSeek Coder V2 16B",
        ollama_name="deepseek-coder-v2:16b",
        params_b=16,
        ram_gb=20,
        vram_gb=12,
        size_gb=8.9,
        tags=("coder", "quality"),
        description="Excelente raciocínio em código. Workstation recomendada.",
        tier="high",
    ),
    ModelEntry(
        id="qwen2.5-coder-32b",
        name="Qwen2.5 Coder 32B",
        ollama_name="qwen2.5-coder:32b",
        params_b=32,
        ram_gb=32,
        vram_gb=24,
        size_gb=19.0,
        tags=("coder", "quality", "high-end"),
        description="Topo de linha local. Requer 32 GB RAM ou GPU 24 GB+.",
        tier="ultra",
    ),
    ModelEntry(
        id="llama3.2-3b",
        name="Llama 3.2 3B",
        ollama_name="llama3.2:3b",
        params_b=3,
        ram_gb=6,
        vram_gb=4,
        size_gb=2.0,
        tags=("general", "fast"),
        description="Modelo geral leve quando o foco não é só código.",
        tier="low",
    ),
]

TIER_ORDER = {"minimal": 0, "low": 1, "medium": 2, "high": 3, "ultra": 4}


def resolve_model_for_run(requested: Optional[str], installed: List[str], hardware: Dict[str, Any]) -> str:
    """Pick the best model name for an agent run."""
    if requested and str(requested).strip():
        return str(requested).strip()

    rec = recommend_models(hardware, installed)
    primary = rec["primary"]["ollama_name"]
    if _is_model_installed(primary, installed):
        return primary

    for name in installed:
        lower = name.lower()
        if any(tag in lower for tag in ("coder", "qwen", "deepseek", "codellama")):
            return name

    if installed:
        return installed[0]
    return primary


def _is_model_installed(ollama_name: str, installed: List[str]) -> bool:
    if ollama_name in installed:
        return True
    base = ollama_name.split(":")[0]
    return any(name.split(":")[0] == base for name in installed)


def _fits_hardware(entry: ModelEntry, hardware: Dict[str, Any]) -> bool:
    effective = float(hardware.get("effective_memory_gb") or 0)
    has_gpu = bool(hardware.get("has_gpu"))
    required = entry.vram_gb if has_gpu and entry.vram_gb else entry.ram_gb
    return effective >= required * 0.95


def _score(entry: ModelEntry, hardware: Dict[str, Any]) -> float:
    if not _fits_hardware(entry, hardware):
        return -1.0
    tier = hardware.get("tier", "medium")
    tier_idx = TIER_ORDER.get(tier, 2)
    entry_idx = TIER_ORDER.get(entry.tier, 2)
    score = 100.0 - abs(entry_idx - tier_idx) * 15
    if "coder" in entry.tags:
        score += 20
    if "recommended" in entry.tags or "default" in entry.tags:
        score += 10
    if "fast" in entry.tags and tier in {"minimal", "low"}:
        score += 8
    if "quality" in entry.tags and tier in {"high", "ultra"}:
        score += 8
    return score


def recommend_models(
    hardware: Dict[str, Any],
    installed: Optional[List[str]] = None,
) -> Dict[str, Any]:
    ranked = sorted(MODEL_CATALOG, key=lambda e: _score(e, hardware), reverse=True)
    fitting = [e for e in ranked if _score(e, hardware) >= 0]

    primary = fitting[0] if fitting else MODEL_CATALOG[0]
    alternatives = [e for e in fitting[1:4]]

    catalog: List[Dict[str, Any]] = []
    for entry in MODEL_CATALOG:
        item = entry.to_dict()
        item["fits"] = _fits_hardware(entry, hardware)
        item["installed"] = _is_model_installed(entry.ollama_name, installed or [])
        item["score"] = _score(entry, hardware)
        item["recommended"] = entry.id == primary.id
        catalog.append(item)

    return {
        "hardware": hardware,
        "tier": hardware.get("tier"),
        "effective_memory_gb": hardware.get("effective_memory_gb"),
        "primary": {**primary.to_dict(), "fits": _fits_hardware(primary, hardware), "installed": _is_model_installed(primary.ollama_name, installed or []), "recommended": True},
        "alternatives": [
            {**e.to_dict(), "fits": _fits_hardware(e, hardware), "installed": _is_model_installed(e.ollama_name, installed or [])}
            for e in alternatives
        ],
        "catalog": catalog,
        "installed": list(installed or []),
    }
