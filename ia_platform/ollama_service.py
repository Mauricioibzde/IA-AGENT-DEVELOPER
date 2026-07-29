"""Start, install, and monitor the local Ollama daemon for Forge."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional


STARTUP_TIMEOUT = 45.0
INSTALL_TIMEOUT = 900.0
POLL_INTERVAL = 0.5
StatusCallback = Optional[Callable[[str], None]]


class OllamaServiceManager:
    """Ensure Ollama is installed, running, and reachable over HTTP."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen[Any]] = None
        self._started_by_us = False

    def _emit(self, callback: StatusCallback, message: str) -> None:
        if callback:
            callback(message)

    def _windows_candidate_paths(self) -> List[str]:
        paths: List[str] = []
        local = os.environ.get("LOCALAPPDATA") or ""
        program_files = os.environ.get("ProgramFiles") or ""
        program_files_x86 = os.environ.get("ProgramFiles(x86)") or ""
        for base in (local, program_files, program_files_x86):
            if base:
                paths.append(os.path.join(base, "Programs", "Ollama", "ollama.exe"))
                paths.append(os.path.join(base, "Ollama", "ollama.exe"))
        return paths

    def _refresh_windows_path(self) -> None:
        if platform.system() != "Windows":
            return
        try:
            import winreg

            chunks: List[str] = []
            for hive, subkey in (
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                (winreg.HKEY_CURRENT_USER, r"Environment"),
            ):
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        chunks.append(str(winreg.QueryValueEx(key, "Path")[0]))
                except OSError:
                    continue
            merged = ";".join(ch for ch in chunks if ch)
            if merged:
                os.environ["PATH"] = merged + ";" + os.environ.get("PATH", "")
        except Exception:
            pass

    def binary_path(self) -> Optional[str]:
        found = shutil.which("ollama")
        if found:
            return found
        if platform.system() == "Windows":
            for path in self._windows_candidate_paths():
                if os.path.isfile(path):
                    return path
        return None

    def is_installed(self) -> bool:
        return self.binary_path() is not None

    def is_api_ready(self, host: str, timeout: float = 2.0) -> bool:
        try:
            req = urllib.request.Request(f"{host.rstrip('/')}/api/tags")
            with urllib.request.urlopen(req, timeout=timeout):
                return True
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False

    def install(self, status_cb: StatusCallback = None) -> Dict[str, Any]:
        """Attempt to install Ollama on the local machine."""
        if self.is_installed():
            return {"ok": True, "installed": True, "message": "Ollama já instalado."}

        system = platform.system()
        if system == "Windows":
            return self._install_windows(status_cb)
        if system == "Linux":
            return self._install_linux(status_cb)
        if system == "Darwin":
            return self._install_macos(status_cb)
        return {
            "ok": False,
            "installed": False,
            "error": "Instalação automática não suportada neste sistema operacional.",
            "install_url": "https://ollama.com/download",
        }

    def _wait_for_binary(self, status_cb: StatusCallback, seconds: float = 90.0) -> bool:
        deadline = time.time() + seconds
        while time.time() < deadline:
            if platform.system() == "Windows":
                self._refresh_windows_path()
            if self.is_installed():
                return True
            self._emit(status_cb, "Aguardando Ollama ficar disponível...")
            time.sleep(2)
        return self.is_installed()

    def _install_windows(self, status_cb: StatusCallback) -> Dict[str, Any]:
        if shutil.which("winget"):
            self._emit(status_cb, "Instalando Ollama via winget (pode levar alguns minutos)...")
            try:
                completed = subprocess.run(
                    [
                        "winget",
                        "install",
                        "--id",
                        "Ollama.Ollama",
                        "-e",
                        "--accept-package-agreements",
                        "--accept-source-agreements",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=INSTALL_TIMEOUT,
                )
                output = (completed.stdout or "") + (completed.stderr or "")
                if completed.returncode not in (0,):
                    # winget returns 2316632107 (-1978335213 unsigned) when already installed
                    if "already installed" not in output.lower() and "já instalado" not in output.lower():
                        if not self._wait_for_binary(status_cb, seconds=5):
                            pass  # try installer fallback below if still missing
            except subprocess.TimeoutExpired:
                return {"ok": False, "installed": False, "error": "Timeout ao instalar Ollama via winget."}
            except OSError as exc:
                self._emit(status_cb, f"winget falhou ({exc}); tentando instalador...")

        if self._wait_for_binary(status_cb, seconds=10):
            return {"ok": True, "installed": True, "message": "Ollama instalado com sucesso."}

        self._emit(status_cb, "Baixando instalador do Ollama...")
        installer = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
        try:
            urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer)
        except Exception as exc:
            return {
                "ok": False,
                "installed": False,
                "error": f"Falha ao baixar Ollama: {exc}",
                "install_url": "https://ollama.com/download",
            }

        self._emit(status_cb, "Executando instalador do Ollama...")
        try:
            subprocess.run(
                [installer, "/VERYSILENT", "/NORESTART"],
                timeout=INSTALL_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "installed": False, "error": "Timeout durante instalação do Ollama."}
        except OSError as exc:
            return {"ok": False, "installed": False, "error": f"Falha ao executar instalador: {exc}"}

        if self._wait_for_binary(status_cb):
            return {"ok": True, "installed": True, "message": "Ollama instalado com sucesso."}
        return {
            "ok": False,
            "installed": False,
            "error": "Ollama instalado, mas não encontrado no PATH. Reinicie a aplicação.",
            "install_url": "https://ollama.com/download",
        }

    def _install_linux(self, status_cb: StatusCallback) -> Dict[str, Any]:
        if not shutil.which("curl"):
            return {
                "ok": False,
                "installed": False,
                "error": "curl não encontrado. Instale Ollama manualmente: https://ollama.com/download",
                "install_url": "https://ollama.com/download/linux",
            }
        self._emit(status_cb, "Instalando Ollama via script oficial (pode pedir senha sudo)...")
        try:
            subprocess.run(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                timeout=INSTALL_TIMEOUT,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            return {
                "ok": False,
                "installed": False,
                "error": f"Instalação Linux falhou (exit {exc.returncode}).",
                "install_url": "https://ollama.com/download/linux",
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "installed": False, "error": "Timeout ao instalar Ollama no Linux."}

        if self._wait_for_binary(status_cb):
            return {"ok": True, "installed": True, "message": "Ollama instalado com sucesso."}
        return {
            "ok": False,
            "installed": False,
            "error": "Ollama instalado, mas não encontrado no PATH. Reinicie a aplicação.",
        }

    def _install_macos(self, status_cb: StatusCallback) -> Dict[str, Any]:
        if shutil.which("brew"):
            self._emit(status_cb, "Instalando Ollama via Homebrew...")
            try:
                subprocess.run(["brew", "install", "ollama"], timeout=INSTALL_TIMEOUT, check=True)
            except subprocess.CalledProcessError as exc:
                return {"ok": False, "installed": False, "error": f"brew install falhou (exit {exc.returncode})."}
            except subprocess.TimeoutExpired:
                return {"ok": False, "installed": False, "error": "Timeout ao instalar Ollama via Homebrew."}
            if self._wait_for_binary(status_cb):
                return {"ok": True, "installed": True, "message": "Ollama instalado com sucesso."}

        return {
            "ok": False,
            "installed": False,
            "error": "Instale Ollama em https://ollama.com/download/mac ou instale Homebrew e tente novamente.",
            "install_url": "https://ollama.com/download/mac",
        }

    def ensure_running(
        self,
        host: str,
        *,
        auto_install: bool = False,
        status_cb: StatusCallback = None,
    ) -> Dict[str, Any]:
        """Return status dict; install and/or start Ollama when needed."""
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
                if auto_install:
                    self._emit(status_cb, "Ollama não encontrado — iniciando instalação...")
                    install_result = self.install(status_cb=status_cb)
                    if not install_result.get("ok"):
                        return {
                            **install_result,
                            "ollama": False,
                            "installed": install_result.get("installed", False),
                        }
                else:
                    return {
                        "ok": False,
                        "ollama": False,
                        "installed": False,
                        "error": (
                            "Ollama não encontrado. Use Configurar automaticamente "
                            "para instalar e iniciar."
                        ),
                        "install_url": "https://ollama.com/download",
                    }

            self._emit(status_cb, "Iniciando Ollama...")
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
