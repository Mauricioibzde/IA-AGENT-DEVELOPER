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
    return resolve_models_for_run(requested, installed, hardware)["coder"]


def _pick_light_aux_model(installed: List[str], coder: str, hardware: Dict[str, Any]) -> Optional[str]:
    """Pick a smaller installed model for planner/reflection on low-end hardware."""
    tier = hardware.get("tier", "medium")
    if tier not in {"minimal", "low"}:
        return None

    for entry in MODEL_CATALOG:
        if entry.tier not in {"minimal", "low"}:
            continue
        if entry.ollama_name == coder:
            continue
        if entry.ollama_name in installed:
            return entry.ollama_name

    for name in installed:
        if name == coder:
            continue
        lower = name.lower()
        if any(tag in lower for tag in ("1.5b", "1b", ":3b", "3b")):
            return name
    return None


def resolve_models_for_run(
    requested: Optional[str], installed: List[str], hardware: Dict[str, Any]
) -> Dict[str, str]:
    """Resolve coder/planner/reflection models for an agent run."""
    coder = _resolve_coder_model(requested, installed, hardware)
    aux = None if requested and str(requested).strip() else _pick_light_aux_model(installed, coder, hardware)
    planner = aux or coder
    reflection = aux or coder
    return {"coder": coder, "planner": planner, "reflection": reflection}


def resolve_model_for_chat(
    requested: Optional[str], installed: List[str], hardware: Optional[Dict[str, Any]] = None
) -> str:
    """Prefer conversational / instruct models for Chat mode (avoid *-base)."""
    hardware = hardware or {}
    if requested and str(requested).strip():
        name = str(requested).strip()
        if not name.lower().endswith("-base"):
            return name

    preferred = [
        "llama3.2:3b",
        "llama3.2",
        "llama3.1:8b",
        "llama3.1",
        "mistral:7b",
        "mistral",
        "qwen2.5:7b",
        "qwen2.5",
        "qwen2.5-coder:7b",
        "qwen2.5-coder:3b",
        "codellama:latest",
        "codellama:7b",
    ]
    for candidate in preferred:
        hit = _installed_model_name(candidate, installed)
        if hit and not hit.lower().endswith("-base"):
            return hit

    scored: List[tuple[int, str]] = []
    for name in installed:
        lower = name.lower()
        if "embed" in lower or lower.endswith("-base"):
            continue
        score = 0
        if any(tag in lower for tag in ("llama3.2", "llama3.1", "mistral", "qwen2.5")):
            score += 40
        if "coder" in lower:
            score += 10
        if any(tag in lower for tag in (":3b", "3b", "1.5b", "tiny", "mini")):
            score += 15
        if any(tag in lower for tag in (":7b", "7b", "8b")):
            score += 8
        scored.append((score, name))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored[0][1]

    return _resolve_coder_model(None, installed, hardware)


def _resolve_coder_model(requested: Optional[str], installed: List[str], hardware: Dict[str, Any]) -> str:
    if requested and str(requested).strip():
        return str(requested).strip()

    rec = recommend_models(hardware, installed)
    primary = rec["primary"]["ollama_name"]
    installed_primary = _installed_model_name(primary, installed)
    if installed_primary:
        return installed_primary

    for name in installed:
        lower = name.lower()
        if any(tag in lower for tag in ("coder", "qwen", "deepseek", "codellama")):
            return name

    if installed:
        return installed[0]
    return primary


def _is_model_installed(ollama_name: str, installed: List[str]) -> bool:
    return _installed_model_name(ollama_name, installed) is not None


def _installed_model_name(ollama_name: str, installed: List[str]) -> Optional[str]:
    if ollama_name in installed:
        return ollama_name
    base = ollama_name.split(":")[0]
    for name in installed:
        if name.split(":")[0] == base:
            return name
    return None


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


def recommend_setup_model(
    hardware: Dict[str, Any],
    installed: Optional[List[str]] = None,
) -> str:
    """Pick the best first-time download model (CPU/GPU aware)."""
    installed = installed or []
    has_gpu = bool(hardware.get("has_gpu") or hardware.get("gpus"))

    if has_gpu:
        return recommend_models(hardware, installed)["primary"]["ollama_name"]

    # CPU-only: prefer smaller coder models that fit RAM
    candidates: List[tuple[float, ModelEntry]] = []
    for entry in MODEL_CATALOG:
        if "coder" not in entry.tags:
            continue
        if not _fits_hardware(entry, hardware):
            continue
        score = _score(entry, hardware)
        score += max(0.0, 18.0 - entry.size_gb * 4.0)
        if entry.tier in {"minimal", "low"}:
            score += 18.0
        elif entry.tier == "medium":
            score += 6.0
        candidates.append((score, entry))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        chosen = candidates[0][1].ollama_name
        installed_chosen = _installed_model_name(chosen, installed)
        if installed_chosen:
            return installed_chosen
        for _score_val, entry in candidates:
            installed_entry = _installed_model_name(entry.ollama_name, installed)
            if installed_entry:
                return installed_entry
        return chosen

    exact_installed = [
        entry
        for entry in MODEL_CATALOG
        if entry.ollama_name in installed and "coder" in entry.tags
    ]
    if exact_installed:
        exact_installed.sort(key=lambda entry: (TIER_ORDER.get(entry.tier, 2), entry.size_gb))
        return exact_installed[0].ollama_name

    fallback = recommend_models(hardware, installed)["primary"]["ollama_name"]
    return _installed_model_name(fallback, installed) or fallback


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
