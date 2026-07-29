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


def test_apple_silicon_unified_memory(monkeypatch) -> None:
    import ia_platform.hardware as hwmod

    monkeypatch.setattr(hwmod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(hwmod.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(hwmod.platform, "release", lambda: "23.0.0")
    monkeypatch.setattr(hwmod, "_detect_memory", lambda: (16.0, 12.0))
    monkeypatch.setattr(hwmod, "_detect_nvidia_gpus", lambda: [])
    monkeypatch.setattr(
        hwmod,
        "_detect_apple_gpu",
        lambda: {"vendor": "apple", "name": "Apple M2", "vram_total_gb": 0.0, "vram_free_gb": 0.0},
    )
    profile = hwmod.detect_hardware()
    assert profile["has_gpu"] is True
    assert profile["vram_total_gb"] > 0


def test_detect_linux_amd_gpu(monkeypatch) -> None:
    import ia_platform.hardware as hwmod

    monkeypatch.setattr(hwmod.platform, "system", lambda: "Linux")

    class FakeFile:
        def __init__(self, content):
            self._content = content

        def read_text(self, encoding="utf-8"):
            if self._content is None:
                raise OSError("missing")
            return self._content

    class FakeDevice:
        def is_dir(self):
            return True

        def resolve(self):
            return self

        def __truediv__(self, key):
            files = {
                "vendor": "0x1002\n",
                "product": "AMD Radeon RX 6800\n",
                "mem_info_vram_total": "17179869184\n",
            }
            return FakeFile(files.get(key))

    class FakeCard:
        name = "card0"

        def __truediv__(self, key):
            if key == "device":
                return FakeDevice()
            raise KeyError(key)

        @property
        def device(self):
            return FakeDevice()

    class FakeDrmRoot:
        def is_dir(self):
            return True

        def iterdir(self):
            return [FakeCard()]

    monkeypatch.setattr(hwmod, "Path", lambda p: FakeDrmRoot() if p == "/sys/class/drm" else hwmod.Path(p))
    gpus = hwmod._detect_linux_drm_gpus()
    assert len(gpus) == 1
    assert gpus[0]["vendor"] == "amd"
    assert gpus[0]["vram_total_gb"] == 16.0


def test_detect_linux_intel_gpu(monkeypatch) -> None:
    import ia_platform.hardware as hwmod

    monkeypatch.setattr(hwmod.platform, "system", lambda: "Linux")

    class FakeFile:
        def __init__(self, content):
            self._content = content

        def read_text(self, encoding="utf-8"):
            if self._content is None:
                raise OSError("missing")
            return self._content

    class FakeDevice:
        def is_dir(self):
            return True

        def resolve(self):
            return self

        def __truediv__(self, key):
            files = {
                "vendor": "0x8086\n",
                "product": "Intel UHD Graphics 630\n",
            }
            return FakeFile(files.get(key))

    class FakeCard:
        name = "card0"

        def __truediv__(self, key):
            if key == "device":
                return FakeDevice()
            raise KeyError(key)

        @property
        def device(self):
            return FakeDevice()

    class FakeDrmRoot:
        def is_dir(self):
            return True

        def iterdir(self):
            return [FakeCard()]

    monkeypatch.setattr(hwmod, "Path", lambda p: FakeDrmRoot() if p == "/sys/class/drm" else hwmod.Path(p))
    gpus = hwmod._detect_linux_drm_gpus()
    assert len(gpus) == 1
    assert gpus[0]["vendor"] == "intel"
    assert gpus[0]["shared_memory"] is True

