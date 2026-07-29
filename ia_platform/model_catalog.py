"""Curated Ollama model catalog and hardware-aware recommendations."""

from __future__ import annotations

import re
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


def estimate_model_size_gb(name: str) -> float:
    """Best-effort parameter/size estimate for ranking fallback models."""
    entry = _catalog_entry_for_name(name)
    if entry:
        return float(entry.params_b or entry.size_gb or 99.0)
    match = re.search(r"(\d+(?:\.\d+)?)\s*b\b", (name or "").lower())
    if match:
        return float(match.group(1))
    return 99.0


def pick_smaller_fallback_model(failed: str, installed: List[str]) -> Optional[str]:
    """Pick the best smaller installed model after a load/OOM failure.

    Prefers the largest coder that is still smaller than the failed model.
    """
    failed_name = (failed or "").strip()
    if not failed_name or not installed:
        return None
    failed_size = estimate_model_size_gb(failed_name)
    candidates: List[tuple[float, str]] = []
    for name in installed:
        lower = (name or "").lower()
        if not lower or lower == failed_name.lower():
            continue
        if "embed" in lower or lower.endswith("-base"):
            continue
        size = estimate_model_size_gb(name)
        # Must be meaningfully smaller (avoid 14b when 32b OOM'd on tight hosts).
        if size >= failed_size or size >= max(failed_size * 0.85, failed_size - 0.1):
            continue
        score = size * 10.0
        if "coder" in lower:
            score += 40.0
        if any(tag in lower for tag in (":7b", "7b", "6.7b", "8b")):
            score += 12.0
        if any(tag in lower for tag in (":3b", "3b", "1.5b", "1b")):
            score += 4.0
        candidates.append((score, name))
    if not candidates:
        # Never “fall back” to a larger model (e.g. 6.7b → 32b).
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


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
        "deepseek-coder:6.7b",
        "codellama:latest",
        "codellama:7b",
    ]
    for candidate in preferred:
        hit = _installed_model_name(candidate, installed)
        if hit and not hit.lower().endswith("-base") and _name_fits_hardware(hit, hardware):
            return hit

    scored: List[tuple[int, str]] = []
    for name in installed:
        lower = name.lower()
        if "embed" in lower or lower.endswith("-base"):
            continue
        if not _name_fits_hardware(name, hardware):
            continue
        score = 0
        if any(tag in lower for tag in ("llama3.2", "llama3.1", "mistral", "qwen2.5")):
            score += 40
        if "coder" in lower:
            score += 10
        if any(tag in lower for tag in (":3b", "3b", "1.5b", "tiny", "mini")):
            score += 15
        if any(tag in lower for tag in (":7b", "7b", "8b", "6.7b")):
            score += 8
        # Prefer smaller when multiple fit (avoid picking 32b when 7b also fits).
        if any(tag in lower for tag in (":14b", "14b", ":16b", "16b", ":32b", "32b", ":70b")):
            score -= 25
        scored.append((score, name))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored[0][1]

    return _resolve_coder_model(None, installed, hardware)


def _resolve_coder_model(requested: Optional[str], installed: List[str], hardware: Dict[str, Any]) -> str:
    if requested and str(requested).strip():
        name = str(requested).strip()
        # Explicit pick that cannot load on this host → use a smaller installed coder.
        # (Installed ≠ runnable: qwen2.5-coder:32b often 500s on 16GB boxes.)
        if installed and not _name_fits_hardware(name, hardware):
            alt = pick_smaller_fallback_model(name, installed)
            if alt:
                return alt
            # No smaller option: keep the user's pick (runtime OOM fallback may still help).
            # Never upgrade to a heavier model than requested.
        return name

    rec = recommend_models(hardware, installed)
    primary = rec["primary"]["ollama_name"]
    installed_primary = _installed_model_name(primary, installed)
    if installed_primary and _name_fits_hardware(installed_primary, hardware):
        return installed_primary

    fitting_coders: List[tuple[float, str]] = []
    for name in installed:
        lower = name.lower()
        if "embed" in lower or lower.endswith("-base"):
            continue
        if not any(tag in lower for tag in ("coder", "qwen", "deepseek", "codellama", "llama", "mistral")):
            continue
        if not _name_fits_hardware(name, hardware):
            continue
        entry = _catalog_entry_for_name(name)
        score = _score(entry, hardware) if entry else 50.0
        fitting_coders.append((score, name))
    if fitting_coders:
        fitting_coders.sort(key=lambda item: item[0], reverse=True)
        return fitting_coders[0][1]

    # Nothing fits: prefer the smallest known installed coder as last resort.
    oversized: List[tuple[float, str]] = []
    for name in installed:
        lower = name.lower()
        if "embed" in lower or lower.endswith("-base"):
            continue
        entry = _catalog_entry_for_name(name)
        size = entry.size_gb if entry else 99.0
        oversized.append((size, name))
    if oversized:
        oversized.sort(key=lambda item: item[0])
        return oversized[0][1]

    if installed:
        return installed[0]
    return primary


def _is_model_installed(ollama_name: str, installed: List[str]) -> bool:
    return _installed_model_name(ollama_name, installed) is not None


def _installed_model_name(ollama_name: str, installed: List[str]) -> Optional[str]:
    """Match an installed model without confusing different size tags (7b ≠ 32b)."""
    wanted = (ollama_name or "").strip()
    if not wanted:
        return None
    by_lower = {m.lower(): m for m in installed}
    if wanted.lower() in by_lower:
        return by_lower[wanted.lower()]

    parts = wanted.split(":", 1)
    base = parts[0]
    tag = parts[1] if len(parts) > 1 else ""
    base_l = base.lower()
    tag_l = tag.lower()

    # Same base + same tag (or tag prefix, e.g. 7b vs 7b-instruct).
    for name in installed:
        n_parts = name.split(":", 1)
        n_base = n_parts[0]
        n_tag = n_parts[1] if len(n_parts) > 1 else ""
        if n_base.lower() != base_l:
            continue
        if tag_l and n_tag.lower() == tag_l:
            return name
        if tag_l and n_tag.lower().startswith(tag_l + "-"):
            return name
        if tag_l and tag_l.startswith(n_tag.lower() + "-") and n_tag:
            return name

    # Untagged request (e.g. "llama3.2") may use any installed variant of that base.
    if not tag_l:
        for name in installed:
            if name.split(":", 1)[0].lower() == base_l:
                return name
    return None


def _catalog_entry_for_name(name: str) -> Optional[ModelEntry]:
    lower = (name or "").lower()
    for entry in MODEL_CATALOG:
        if entry.ollama_name.lower() == lower:
            return entry
    # Exact base+tag family: qwen2.5-coder:7b-instruct → qwen2.5-coder:7b
    base_tag = lower.split(":", 1)
    if len(base_tag) == 2:
        base, tag = base_tag
        for entry in MODEL_CATALOG:
            e_base, e_tag = (entry.ollama_name.split(":", 1) + [""])[:2]
            if e_base.lower() == base and tag.startswith(e_tag.lower()) and e_tag:
                return entry
    return None


def _name_fits_hardware(name: str, hardware: Dict[str, Any]) -> bool:
    entry = _catalog_entry_for_name(name)
    if entry:
        return _fits_hardware(entry, hardware)
    # Unknown install: allow (cannot prove it won't fit).
    return True


def _fits_hardware(entry: ModelEntry, hardware: Dict[str, Any]) -> bool:
    """Return True if the model can plausibly run given RAM and/or GPU VRAM.

    Ollama can keep layers in RAM while offloading others to GPU, so a machine
    with lots of RAM and a modest GPU may still run larger coder models.
    """
    ram_avail = float(
        hardware.get("ram_available_gb")
        or hardware.get("ram_total_gb")
        or 0
    )
    vram_free = float(
        hardware.get("vram_free_gb")
        or hardware.get("vram_total_gb")
        or 0
    )
    has_gpu = bool(hardware.get("has_gpu"))
    effective = float(hardware.get("effective_memory_gb") or 0)

    # Enough system RAM alone (CPU / heavy RAM path).
    if ram_avail >= entry.ram_gb * 0.95:
        return True
    # Enough dedicated VRAM alone.
    if has_gpu and entry.vram_gb and vram_free >= entry.vram_gb * 0.95:
        return True
    # Hybrid offload: partial VRAM + remaining layers in RAM.
    if has_gpu and (vram_free + ram_avail * 0.55) >= entry.ram_gb * 0.9:
        return True
    # Back-compat for callers that only set effective_memory_gb.
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

    # Prefer exact installed coder tags that fit hardware.
    fitting_installed: List[tuple[float, str]] = []
    oversized_installed: List[tuple[float, str]] = []
    for entry in MODEL_CATALOG:
        if "coder" not in entry.tags:
            continue
        if entry.ollama_name not in installed:
            continue
        score = _score(entry, hardware)
        if score < 0:
            # Keep as last resort only — installed ≠ runnable on this machine.
            oversized_installed.append((entry.size_gb, entry.ollama_name))
            continue
        score += min(entry.size_gb, 8.0) * 0.5
        fitting_installed.append((score, entry.ollama_name))
    if fitting_installed:
        fitting_installed.sort(key=lambda item: item[0], reverse=True)
        return fitting_installed[0][1]

    # Fuzzy match (tag family) only when an installed variant fits.
    for entry in MODEL_CATALOG:
        if "coder" not in entry.tags:
            continue
        name = _installed_model_name(entry.ollama_name, installed)
        if name and name in installed and _name_fits_hardware(name, hardware):
            return name

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
        return candidates[0][1].ollama_name

    # Nothing fits to download: fall back to smallest oversized install.
    if oversized_installed:
        oversized_installed.sort(key=lambda item: item[0])
        return oversized_installed[0][1]

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
