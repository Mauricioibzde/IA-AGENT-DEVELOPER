"""Tests for Ollama auto-start service."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock

import pytest

_PATH = Path(__file__).resolve().parent / "ollama_service.py"
_spec = importlib.util.spec_from_file_location("ia_platform_ollama_service", _PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_mod)
OllamaServiceManager = _mod.OllamaServiceManager


def test_is_api_ready_true() -> None:
    mgr = OllamaServiceManager()
    with mock.patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value = mock.Mock()
        assert mgr.is_api_ready("http://127.0.0.1:11434") is True


def test_ensure_running_when_already_online() -> None:
    mgr = OllamaServiceManager()
    with mock.patch.object(mgr, "is_api_ready", return_value=True):
        result = mgr.ensure_running("http://127.0.0.1:11434")
    assert result["ok"] is True
    assert result["started"] is False


def test_ensure_running_not_installed() -> None:
    mgr = OllamaServiceManager()
    with mock.patch.object(mgr, "is_api_ready", return_value=False):
        with mock.patch.object(mgr, "is_installed", return_value=False):
            result = mgr.ensure_running("http://127.0.0.1:11434", auto_install=False)
    assert result["ok"] is False
    assert result["installed"] is False
    assert "configurar" in result["error"].lower() or "automaticamente" in result["error"].lower()


def test_ensure_running_starts_process() -> None:
    mgr = OllamaServiceManager()
    proc = mock.Mock()
    proc.poll.return_value = None
    proc.stderr = None

    with mock.patch.object(mgr, "is_api_ready", side_effect=[False, True]):
        with mock.patch.object(mgr, "is_installed", return_value=True):
            with mock.patch.object(mgr, "binary_path", return_value="/usr/bin/ollama"):
                with mock.patch("subprocess.Popen", return_value=proc) as popen:
                    result = mgr.ensure_running("http://127.0.0.1:11434")
    assert result["ok"] is True
    assert result["started"] is True
    popen.assert_called_once()


def test_ensure_running_auto_install_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = OllamaServiceManager()
    with mock.patch.object(mgr, "is_api_ready", return_value=False):
        with mock.patch.object(mgr, "is_installed", return_value=False):
            with mock.patch.object(
                mgr,
                "install",
                return_value={"ok": True, "installed": True, "message": "installed"},
            ) as install:
                with mock.patch.object(mgr, "_start_process"):
                    with mock.patch.object(mgr, "is_api_ready", side_effect=[False, True]):
                        result = mgr.ensure_running("http://127.0.0.1:11434", auto_install=True)
    install.assert_called_once()
    assert result["ok"] is True


def test_install_windows_winget(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = OllamaServiceManager()
    with mock.patch("platform.system", return_value="Windows"):
        with mock.patch.object(mgr, "is_installed", side_effect=[False, True]):
            with mock.patch("shutil.which", side_effect=lambda name: "winget.exe" if name == "winget" else None):
                with mock.patch("subprocess.run") as run:
                    with mock.patch.object(mgr, "_wait_for_binary", return_value=True):
                        result = mgr.install()
    run.assert_called_once()
    assert result["ok"] is True


def test_install_linux_uses_sudo_n_and_zstd(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = OllamaServiceManager()
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd) if isinstance(cmd, (list, tuple)) else [str(cmd)])
        return mock.Mock(returncode=0, stdout="", stderr="")

    with mock.patch("platform.system", return_value="Linux"):
        with mock.patch.object(mgr, "is_installed", side_effect=[False, True]):
            with mock.patch.object(mgr, "_can_sudo_n", return_value=True):
                with mock.patch.object(mgr, "_ensure_linux_extract_tools", return_value=None):
                    with mock.patch("shutil.which", side_effect=lambda name: "/usr/bin/curl" if name == "curl" else "/usr/bin/zstd" if name == "zstd" else None):
                        with mock.patch("subprocess.run", side_effect=fake_run):
                            with mock.patch.object(mgr, "_wait_for_binary", return_value=True):
                                result = mgr.install()
    assert result["ok"] is True
    # Official install should pipe through sudo -n sh
    assert any("sudo -n sh" in " ".join(c) or (len(c) >= 3 and "curl" in " ".join(c)) for c in calls)


def test_ensure_linux_extract_tools_reports_missing_zstd() -> None:
    mgr = OllamaServiceManager()
    with mock.patch.object(mgr, "_can_sudo_n", return_value=False):
        with mock.patch("shutil.which", return_value=None):
            err = mgr._ensure_linux_extract_tools(None)
    assert err is not None
    assert "zstd" in err.lower()
