"""Persisted user settings (hardware profile override for recommendations)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
DEFAULT_SETTINGS_PATH = REPO_ROOT / ".forge" / "settings.json"

_LOCK = threading.Lock()

HARDWARE_PRESETS: Dict[str, Dict[str, Any]] = {
    "notebook-8": {
        "label": "Notebook 8 GB",
        "ram_total_gb": 8,
        "vram_total_gb": 0,
        "has_gpu": False,
        "cpu_cores": 4,
    },
    "notebook-16": {
        "label": "Notebook 16 GB",
        "ram_total_gb": 16,
        "vram_total_gb": 0,
        "has_gpu": False,
        "cpu_cores": 8,
    },
    "desktop-16-gpu8": {
        "label": "Desktop 16 GB + GPU 8 GB",
        "ram_total_gb": 16,
        "vram_total_gb": 8,
        "has_gpu": True,
        "cpu_cores": 8,
    },
    "desktop-32-gpu8": {
        "label": "Desktop 32 GB + GPU 8 GB",
        "ram_total_gb": 32,
        "vram_total_gb": 8,
        "has_gpu": True,
        "cpu_cores": 12,
    },
    "desktop-40-gpu8": {
        "label": "Desktop 40 GB+ + GPU 8 GB",
        "ram_total_gb": 40,
        "vram_total_gb": 8,
        "has_gpu": True,
        "cpu_cores": 12,
    },
    "desktop-64-gpu8": {
        "label": "Desktop 64 GB + GPU 8 GB",
        "ram_total_gb": 64,
        "vram_total_gb": 8,
        "has_gpu": True,
        "cpu_cores": 16,
    },
    "workstation-64-gpu24": {
        "label": "Workstation 64 GB + GPU 24 GB",
        "ram_total_gb": 64,
        "vram_total_gb": 24,
        "has_gpu": True,
        "cpu_cores": 16,
    },
}


def default_settings() -> Dict[str, Any]:
    return {
        "hardware_mode": "detected",  # detected | manual
        "hardware_preset": "",
        "hardware_profile": {
            "ram_total_gb": None,
            "vram_total_gb": None,
            "has_gpu": None,
            "cpu_cores": None,
            "gpu_name": "",
        },
        "preferred_model": None,
    }


def load_settings(path: Optional[Path] = None) -> Dict[str, Any]:
    settings_path = path or DEFAULT_SETTINGS_PATH
    base = default_settings()
    if not settings_path.is_file():
        return base
    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return base
    if not isinstance(raw, dict):
        return base
    merged = default_settings()
    merged.update({k: raw[k] for k in merged.keys() if k in raw})
    profile = raw.get("hardware_profile")
    if isinstance(profile, dict):
        merged["hardware_profile"] = {**default_settings()["hardware_profile"], **profile}
    return merged


def save_settings(data: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    settings_path = path or DEFAULT_SETTINGS_PATH
    current = load_settings(settings_path)
    incoming = dict(data or {})

    mode = str(incoming.get("hardware_mode") or current.get("hardware_mode") or "detected").strip().lower()
    if mode not in {"detected", "manual"}:
        mode = "detected"
    current["hardware_mode"] = mode

    preset = str(incoming.get("hardware_preset") or "").strip()
    if preset and preset not in HARDWARE_PRESETS:
        raise ValueError(f"Preset desconhecido: {preset}")
    if preset:
        current["hardware_preset"] = preset
        preset_data = HARDWARE_PRESETS[preset]
        current["hardware_profile"] = {
            "ram_total_gb": preset_data["ram_total_gb"],
            "vram_total_gb": preset_data["vram_total_gb"],
            "has_gpu": preset_data["has_gpu"],
            "cpu_cores": preset_data.get("cpu_cores"),
            "gpu_name": current.get("hardware_profile", {}).get("gpu_name") or "",
        }
        current["hardware_mode"] = "manual"
    elif "hardware_profile" in incoming and isinstance(incoming["hardware_profile"], dict):
        base_profile = current.get("hardware_profile")
        if not isinstance(base_profile, dict):
            base_profile = {}
        profile = dict(base_profile)
        profile.update(incoming["hardware_profile"])
        current["hardware_profile"] = _normalize_profile(profile)
        current["hardware_preset"] = str(incoming.get("hardware_preset") or "")
        if mode == "manual":
            current["hardware_mode"] = "manual"

    if "preferred_model" in incoming:
        pref = incoming.get("preferred_model")
        current["preferred_model"] = str(pref).strip() if pref else None

    if "hardware_mode" in incoming and not preset:
        current["hardware_mode"] = mode

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        settings_path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return current


def _normalize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    def _num(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _int(value: Any) -> Optional[int]:
        n = _num(value)
        return int(n) if n is not None else None

    has_gpu = profile.get("has_gpu")
    if isinstance(has_gpu, str):
        has_gpu = has_gpu.strip().lower() in {"1", "true", "yes", "sim"}
    elif has_gpu is not None:
        has_gpu = bool(has_gpu)

    return {
        "ram_total_gb": _num(profile.get("ram_total_gb")),
        "vram_total_gb": _num(profile.get("vram_total_gb")),
        "has_gpu": has_gpu,
        "cpu_cores": _int(profile.get("cpu_cores")),
        "gpu_name": str(profile.get("gpu_name") or "").strip()[:120],
    }


def settings_public(settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = settings if settings is not None else load_settings()
    return {
        **data,
        "presets": [
            {"id": key, **value}
            for key, value in HARDWARE_PRESETS.items()
        ],
    }
