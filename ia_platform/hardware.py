"""Detect local hardware for model recommendations."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

VENDOR_AMD = "0x1002"
VENDOR_INTEL = "0x8086"
VENDOR_NVIDIA = "0x10de"


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


def _is_wsl() -> bool:
    if platform.system() != "Linux":
        return False
    if Path("/proc/sys/fs/binfmt_misc/WSLInterop").exists():
        return True
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "microsoft" in version or "wsl" in version


def _is_container() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(token in cgroup for token in ("docker", "containerd", "kubepods", "podman"))


def _detect_memory() -> tuple[float, float]:
    system = platform.system()
    if system == "Windows":
        readers = (_read_windows_memory,)
    elif system == "Darwin":
        readers = (_read_macos_memory,)
    else:
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


def _read_sysfs_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_sysfs_int(path: Path) -> Optional[int]:
    raw = _read_sysfs_text(path)
    if not raw:
        return None
    try:
        if raw.lower().startswith("0x"):
            return int(raw, 16)
        return int(raw)
    except ValueError:
        return None


def _gpu_name_from_sysfs(device_dir: Path) -> str:
    for name_path in (device_dir / "product", device_dir / "name"):
        name = _read_sysfs_text(name_path)
        if name:
            return name
    uevent = _read_sysfs_text(device_dir / "uevent") or ""
    for line in uevent.splitlines():
        if line.startswith("PCI_ID="):
            return line.split("=", 1)[1].strip()
    vendor = _read_sysfs_text(device_dir / "vendor") or ""
    device = _read_sysfs_text(device_dir / "device") or ""
    return f"GPU {vendor}/{device}".strip()


def _detect_linux_drm_gpus() -> List[Dict[str, Any]]:
    if platform.system() != "Linux":
        return []

    drm_root = Path("/sys/class/drm")
    if not drm_root.is_dir():
        return []

    gpus: List[Dict[str, Any]] = []
    seen_devices: set[str] = set()

    for card in sorted(drm_root.iterdir()):
        if not card.name.startswith("card") or not card.name[4:].isdigit():
            continue
        device_dir = card / "device"
        if not device_dir.is_dir():
            continue

        device_key = str(device_dir.resolve())
        if device_key in seen_devices:
            continue
        seen_devices.add(device_key)

        vendor_id = (_read_sysfs_text(device_dir / "vendor") or "").lower()
        if vendor_id not in {VENDOR_AMD, VENDOR_INTEL}:
            continue

        vendor = "amd" if vendor_id == VENDOR_AMD else "intel"
        vram_bytes = _read_sysfs_int(device_dir / "mem_info_vram_total")
        if vram_bytes is None:
            vram_bytes = _read_sysfs_int(device_dir / "mem_info_vram_used")
        vram_total_gb = round(vram_bytes / (1024**3), 1) if vram_bytes else 0.0

        gpus.append(
            {
                "vendor": vendor,
                "name": _gpu_name_from_sysfs(device_dir),
                "vram_total_gb": vram_total_gb,
                "vram_free_gb": vram_total_gb,
                "driver": _read_sysfs_text(device_dir / "driver") or "",
                "shared_memory": vram_total_gb <= 0,
            }
        )
    return gpus


def _detect_rocm_gpus() -> List[Dict[str, Any]]:
    if not shutil.which("rocm-smi"):
        return []
    try:
        output = subprocess.check_output(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--csv"],
            text=True,
            timeout=8,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    lines = [line.strip() for line in output.splitlines() if line.strip() and not line.startswith("=")]
    if len(lines) < 2:
        return []

    headers = [h.strip().lower() for h in lines[0].split(",")]
    gpus: List[Dict[str, Any]] = []
    for row in lines[1:]:
        cols = [c.strip() for c in row.split(",")]
        if len(cols) != len(headers):
            continue
        data = dict(zip(headers, cols))
        name = data.get("card series") or data.get("card model") or data.get("card") or "AMD GPU"
        total_raw = data.get("vram total memory (b)") or data.get("total memory (b)") or ""
        free_raw = data.get("vram free memory (b)") or data.get("free memory (b)") or ""
        try:
            total_gb = round(int(total_raw) / (1024**3), 1) if total_raw else 0.0
            free_gb = round(int(free_raw) / (1024**3), 1) if free_raw else total_gb
        except ValueError:
            total_gb = 0.0
            free_gb = 0.0
        gpus.append(
            {
                "vendor": "amd",
                "name": name,
                "vram_total_gb": total_gb,
                "vram_free_gb": free_gb,
                "driver": "rocm",
            }
        )
    return gpus


def _guess_vendor_from_name(name: str) -> str:
    lower = name.lower()
    if "nvidia" in lower or "geforce" in lower or "quadro" in lower or "rtx" in lower or "gtx" in lower:
        return "nvidia"
    if "amd" in lower or "radeon" in lower or "rx " in lower:
        return "amd"
    if "intel" in lower or "uhd" in lower or "iris" in lower or "arc" in lower:
        return "intel"
    return "unknown"


def _detect_windows_gpus() -> List[Dict[str, Any]]:
    """Enumerate GPUs via WMI when nvidia-smi/rocm are unavailable."""
    if platform.system() != "Windows":
        return []
    ps = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json -Compress"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True,
            timeout=8,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return []
    if not output:
        return []
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        return []

    gpus: List[Dict[str, Any]] = []
    for row in rows:
        name = str(row.get("Name") or "").strip()
        if not name:
            continue
        # Skip Microsoft basic display adapters.
        if "microsoft basic" in name.lower():
            continue
        adapter_ram = row.get("AdapterRAM")
        vram_gb = 0.0
        try:
            # AdapterRAM is often capped/incorrect on modern GPUs; treat as soft hint only.
            if adapter_ram is not None and int(adapter_ram) > 0:
                vram_gb = round(int(adapter_ram) / (1024**3), 1)
        except (TypeError, ValueError):
            vram_gb = 0.0
        gpus.append(
            {
                "vendor": _guess_vendor_from_name(name),
                "name": name,
                "vram_total_gb": vram_gb,
                "vram_free_gb": vram_gb,
                "driver": str(row.get("DriverVersion") or ""),
                "shared_memory": vram_gb <= 0,
                "source": "wmi",
            }
        )
    return gpus


def _merge_gpu_lists(*sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        for gpu in source:
            key = (gpu.get("vendor", ""), gpu.get("name", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(gpu)
    return merged


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


def _runtime_context() -> Dict[str, Any]:
    wsl = _is_wsl()
    container = _is_container()
    if wsl:
        source = "wsl"
    elif container:
        source = "container"
    else:
        source = "native"
    try:
        hostname = socket.gethostname()
    except OSError:
        hostname = "unknown"
    return {
        "hostname": hostname,
        "source": source,
        "is_wsl": wsl,
        "is_container": container,
    }


def detect_hardware() -> Dict[str, Any]:
    """Return a JSON-serializable hardware profile for the machine running Forge."""
    ram_total_gb, ram_available_gb = _detect_memory()
    cpu_cores = os.cpu_count() or 4
    gpus = _merge_gpu_lists(
        _detect_nvidia_gpus(),
        _detect_linux_drm_gpus(),
        _detect_rocm_gpus(),
        _detect_windows_gpus(),
    )
    apple_gpu = _detect_apple_gpu()
    if apple_gpu:
        gpus.append(apple_gpu)

    vram_total = max((g.get("vram_total_gb") or 0) for g in gpus) if gpus else 0.0
    vram_free = max((g.get("vram_free_gb") or 0) for g in gpus) if gpus else 0.0

    # Prefer nvidia-smi VRAM when WMI also listed the same NVIDIA card with bad AdapterRAM.
    nvidia = [g for g in gpus if g.get("vendor") == "nvidia" and g.get("source") != "wmi"]
    if nvidia:
        vram_total = max(g.get("vram_total_gb") or 0 for g in nvidia)
        vram_free = max(g.get("vram_free_gb") or 0 for g in nvidia)

    # Apple Silicon uses unified memory — treat shared RAM as effective VRAM when VRAM is unknown.
    apple_silicon = platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}
    if apple_silicon and any(g.get("vendor") == "apple" for g in gpus) and vram_total <= 0:
        vram_total = round(ram_available_gb * 0.75, 1)
        vram_free = vram_total
        for gpu in gpus:
            if gpu.get("vendor") == "apple":
                gpu["vram_total_gb"] = vram_total
                gpu["vram_free_gb"] = vram_free
                gpu["unified_memory"] = True

    # Integrated AMD/Intel GPUs often report zero dedicated VRAM — use shared RAM estimate.
    if gpus and vram_total <= 0 and not apple_silicon:
        shared_estimate = round(ram_available_gb * 0.5, 1)
        vram_total = shared_estimate
        vram_free = shared_estimate
        for gpu in gpus:
            if gpu.get("shared_memory") or gpu.get("vendor") in {"amd", "intel"}:
                gpu["vram_total_gb"] = shared_estimate
                gpu["vram_free_gb"] = shared_estimate
                gpu["shared_memory"] = True

    has_gpu = bool(gpus) and (vram_total > 0 or apple_silicon)
    tier = _compute_tier(ram_available_gb, vram_total, cpu_cores)
    runtime = _runtime_context()
    os_name = platform.system()
    machine = platform.machine()
    fingerprint = hashlib.sha256(
        f"{os_name}|{machine}|{ram_total_gb}|{cpu_cores}|{runtime['hostname']}".encode("utf-8")
    ).hexdigest()[:12]

    return {
        "os": os_name,
        "os_release": platform.release(),
        "machine": machine,
        "cpu_cores": cpu_cores,
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "has_gpu": has_gpu,
        "gpus": gpus,
        "vram_total_gb": vram_total,
        "vram_free_gb": vram_free,
        "tier": tier,
        "effective_memory_gb": round(max(ram_available_gb * 0.65, vram_free * 0.85), 1),
        "hostname": runtime["hostname"],
        "source": runtime["source"],
        "is_wsl": runtime["is_wsl"],
        "is_container": runtime["is_container"],
        "fingerprint": fingerprint,
        "detected_at": int(time.time()),
        "scope": "server",
        "note": (
            "Hardware do processo Forge (onde o servidor/Ollama rodam). "
            "Se você abrir 127.0.0.1 via túnel/remoto, estes números são da máquina remota — não do PC do navegador."
        ),
    }


def apply_user_hardware_profile(
    detected: Dict[str, Any],
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge detected server hardware with an optional manual 'Meu PC' profile.

    Manual profiles drive recommendations and Auto model choice. Inference still
    runs wherever Ollama is actually hosted.
    """
    from ia_platform.user_settings import load_settings

    cfg = settings if settings is not None else load_settings()
    mode = str(cfg.get("hardware_mode") or "detected").strip().lower()
    out = dict(detected or {})
    out["profile_mode"] = "detected"
    out["detected_hardware"] = {
        "ram_total_gb": detected.get("ram_total_gb"),
        "ram_available_gb": detected.get("ram_available_gb"),
        "vram_total_gb": detected.get("vram_total_gb"),
        "vram_free_gb": detected.get("vram_free_gb"),
        "has_gpu": detected.get("has_gpu"),
        "tier": detected.get("tier"),
        "effective_memory_gb": detected.get("effective_memory_gb"),
        "source": detected.get("source"),
        "hostname": detected.get("hostname"),
        "os": detected.get("os"),
    }

    if mode != "manual":
        out["note"] = (
            "Recomendações usam o hardware detectado do servidor Forge. "
            "Se o seu PC for mais potente, defina o perfil “Meu PC” em Modelos IA."
        )
        return out

    profile = cfg.get("hardware_profile") or {}
    ram = float(profile.get("ram_total_gb") or 0)
    vram = float(profile.get("vram_total_gb") or 0)
    if ram <= 0 and vram <= 0:
        out["note"] = "Perfil manual incompleto — usando hardware detectado do servidor."
        return out

    has_gpu = profile.get("has_gpu")
    if has_gpu is None:
        has_gpu = vram > 0
    has_gpu = bool(has_gpu)
    cpu_cores = profile.get("cpu_cores") or detected.get("cpu_cores") or 4
    try:
        cpu_cores = int(cpu_cores)
    except (TypeError, ValueError):
        cpu_cores = int(detected.get("cpu_cores") or 4)

    ram_available = ram  # user declares usable capacity for recommendations
    vram_free = vram if has_gpu else 0.0
    tier = _compute_tier(ram_available, vram if has_gpu else 0.0, cpu_cores)
    gpu_name = str(profile.get("gpu_name") or "").strip()
    gpus: List[Dict[str, Any]] = []
    if has_gpu:
        gpus = [
            {
                "name": gpu_name or "GPU (perfil do usuário)",
                "vram_total_gb": vram,
                "vram_free_gb": vram_free,
                "source": "user_profile",
            }
        ]

    out.update(
        {
            "ram_total_gb": round(ram, 1),
            "ram_available_gb": round(ram_available, 1),
            "has_gpu": has_gpu,
            "gpus": gpus,
            "vram_total_gb": round(vram, 1) if has_gpu else 0.0,
            "vram_free_gb": round(vram_free, 1) if has_gpu else 0.0,
            "cpu_cores": cpu_cores,
            "tier": tier,
            "effective_memory_gb": round(max(ram_available * 0.65, (vram_free * 0.85 if has_gpu else 0.0)), 1),
            "scope": "user_profile",
            "profile_mode": "manual",
            "hardware_preset": cfg.get("hardware_preset") or "",
            "note": (
                "Recomendações usam o perfil “Meu PC” que você informou. "
                "O chat só usa essa memória de verdade se o Ollama estiver rodando nesse mesmo PC "
                "(não em um container/túnel remoto fraco)."
            ),
        }
    )
    return out
