"""Start and monitor the local Ollama daemon for Forge."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


STARTUP_TIMEOUT = 45.0
POLL_INTERVAL = 0.5


class OllamaServiceManager:
    """Ensure the Ollama HTTP API is reachable, starting `ollama serve` if needed."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen[Any]] = None
        self._started_by_us = False

    def binary_path(self) -> Optional[str]:
        return shutil.which("ollama")

    def is_installed(self) -> bool:
        return self.binary_path() is not None

    def is_api_ready(self, host: str, timeout: float = 2.0) -> bool:
        try:
            req = urllib.request.Request(f"{host.rstrip('/')}/api/tags")
            with urllib.request.urlopen(req, timeout=timeout):
                return True
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False

    def ensure_running(self, host: str) -> Dict[str, Any]:
        """Return status dict; start Ollama when installed but API is down."""
        with self._lock:
            if self.is_api_ready(host):
                return {
                    "ok": True,
                    "ollama": True,
                    "started": False,
                    "installed": True,
                    "message": "Ollama já está online.",
                }

            if not self.is_installed():
                return {
                    "ok": False,
                    "ollama": False,
                    "installed": False,
                    "error": (
                        "Ollama não encontrado no PATH. Instale em https://ollama.com "
                        "e reinicie a aplicação."
                    ),
                    "install_url": "https://ollama.com/download",
                }

            if self._process is None or self._process.poll() is not None:
                self._start_process()

            deadline = time.time() + STARTUP_TIMEOUT
            while time.time() < deadline:
                if self.is_api_ready(host, timeout=2):
                    return {
                        "ok": True,
                        "ollama": True,
                        "started": self._started_by_us,
                        "installed": True,
                        "message": "Ollama iniciado automaticamente.",
                    }
                if self._process and self._process.poll() is not None:
                    stderr = ""
                    if self._process.stderr:
                        try:
                            stderr = self._process.stderr.read() or ""
                        except Exception:
                            stderr = ""
                    return {
                        "ok": False,
                        "ollama": False,
                        "installed": True,
                        "started": False,
                        "error": (
                            "Ollama encerrou inesperadamente."
                            + (f" {stderr[:180]}" if stderr else "")
                        ),
                    }
                time.sleep(POLL_INTERVAL)

            return {
                "ok": False,
                "ollama": False,
                "installed": True,
                "started": False,
                "error": "Ollama não respondeu a tempo. Tente reiniciar o app.",
            }

    def _start_process(self) -> None:
        binary = self.binary_path()
        if not binary:
            raise RuntimeError("ollama binary not found")

        popen_kwargs: Dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.PIPE,
        }
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if creationflags:
                popen_kwargs["creationflags"] = creationflags

        self._process = subprocess.Popen([binary, "serve"], **popen_kwargs)
        self._started_by_us = True

    def stop_if_started(self) -> None:
        with self._lock:
            if not self._started_by_us or not self._process:
                return
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            self._process = None
            self._started_by_us = False


ollama_service = OllamaServiceManager()
