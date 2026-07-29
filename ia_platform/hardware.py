"""Detect local hardware for model recommendations."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional


def _bytes_to_gb(value: int) -> float:
    return round(value / (1024**3), 1)


def _read_linux_meminfo() -> Optional[tuple[int, int]]:
    path = "/proc/meminfo"
    if not os.path.isfile(path):
        return None
    info: Dict[str, int] = {}
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                key, raw = line.split(":", 1)
                info[key.strip()] = int(raw.split()[0]) * 1024
    except OSError:
        return None
    total = info.get("MemTotal")
    if not total:
        return None
    available = info.get("MemAvailable") or info.get("MemFree") or total
    return total, available


def _read_windows_memory() -> Optional[tuple[int, int]]:
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
            return None
        return int(stat.ullTotalPhys), int(stat.ullAvailPhys)
    except Exception:
        return None


def _read_macos_memory() -> Optional[tuple[int, int]]:
    try:
        total_raw = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=3).strip()
        total = int(total_raw)
        # Approximate available via vm_stat is noisy; use 70% of total as conservative available.
        return total, int(total * 0.7)
    except Exception:
        return None


def _detect_memory() -> tuple[float, float]:
    readers = (_read_linux_meminfo, _read_windows_memory, _read_macos_memory)
    for reader in readers:
        data = reader()
        if data:
            total, available = data
            return _bytes_to_gb(total), _bytes_to_gb(available)
    return 8.0, 4.0


def _detect_nvidia_gpus() -> List[Dict[str, Any]]:
    if not shutil.which("nvidia-smi"):
        return []
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    gpus: List[Dict[str, Any]] = []
    for line in output.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            total_mb = float(parts[1])
            free_mb = float(parts[2])
        except ValueError:
            continue
        gpus.append(
            {
                "vendor": "nvidia",
                "name": parts[0],
                "vram_total_gb": round(total_mb / 1024, 1),
                "vram_free_gb": round(free_mb / 1024, 1),
                "driver": parts[3] if len(parts) > 3 else "",
            }
        )
    return gpus


def _detect_apple_gpu() -> Optional[Dict[str, Any]]:
    if platform.system() != "Darwin":
        return None
    try:
        output = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True, timeout=8)
    except (subprocess.SubprocessError, OSError):
        return None
    name_match = re.search(r"Chipset Model:\s*(.+)", output)
    vram_match = re.search(r"VRAM \(Total\):\s*(\d+)\s*MB", output)
    if not name_match:
        return None
    vram_gb = round(int(vram_match.group(1)) / 1024, 1) if vram_match else 0.0
    return {"vendor": "apple", "name": name_match.group(1).strip(), "vram_total_gb": vram_gb, "vram_free_gb": vram_gb}


def _compute_tier(ram_gb: float, vram_gb: float, cpu_cores: int) -> str:
    effective = max(ram_gb * 0.65, vram_gb * 0.85)
    if effective >= 28:
        return "ultra"
    if effective >= 14:
        return "high"
    if effective >= 8:
        return "medium"
    if effective >= 5:
        return "low"
    return "minimal"


def detect_hardware() -> Dict[str, Any]:
    """Return a JSON-serializable hardware profile."""
    ram_total_gb, ram_available_gb = _detect_memory()
    cpu_cores = os.cpu_count() or 4
    gpus = _detect_nvidia_gpus()
    apple_gpu = _detect_apple_gpu()
    if apple_gpu:
        gpus.append(apple_gpu)

    vram_total = max((g.get("vram_total_gb") or 0) for g in gpus) if gpus else 0.0
    vram_free = max((g.get("vram_free_gb") or 0) for g in gpus) if gpus else 0.0
    has_gpu = bool(gpus) and vram_total > 0
    tier = _compute_tier(ram_total_gb, vram_total, cpu_cores)

    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "cpu_cores": cpu_cores,
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "has_gpu": has_gpu,
        "gpus": gpus,
        "vram_total_gb": vram_total,
        "vram_free_gb": vram_free,
        "tier": tier,
        "effective_memory_gb": round(max(ram_available_gb * 0.65, vram_free * 0.85), 1),
    }
