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
            result = mgr.ensure_running("http://127.0.0.1:11434")
    assert result["ok"] is False
    assert result["installed"] is False
    assert "install" in result["error"].lower() or "ollama.com" in result["error"]


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
