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
from pathlib import Path
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
        if platform.system() == "Linux":
            for path in (
                "/usr/local/bin/ollama",
                "/usr/bin/ollama",
                os.path.expanduser("~/.local/bin/ollama"),
                os.path.expanduser("~/.ollama/bin/ollama"),
            ):
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

    def install_url_for_platform(self) -> str:
        system = platform.system()
        if system == "Windows":
            return "https://ollama.com/download/windows"
        if system == "Linux":
            return "https://ollama.com/download/linux"
        if system == "Darwin":
            return "https://ollama.com/download/mac"
        return "https://ollama.com/download"

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

    def _can_sudo_n(self) -> bool:
        if not shutil.which("sudo"):
            return False
        try:
            completed = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return completed.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _ensure_linux_extract_tools(self, status_cb: StatusCallback) -> Optional[str]:
        """Ensure zstd exists (required by current Ollama Linux tarball). Return error or None."""
        if shutil.which("zstd"):
            return None
        self._emit(status_cb, "Instalando dependência zstd (necessária para extrair o Ollama)...")
        if self._can_sudo_n():
            try:
                subprocess.run(
                    ["sudo", "-n", "apt-get", "update", "-qq"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                completed = subprocess.run(
                    ["sudo", "-n", "apt-get", "install", "-y", "-qq", "zstd"],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                )
                if completed.returncode == 0 and shutil.which("zstd"):
                    return None
                detail = ((completed.stderr or "") + (completed.stdout or "")).strip()[:200]
                return f"Falha ao instalar zstd via apt. {detail}".strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                return f"Falha ao instalar zstd: {exc}"
        return (
            "Ollama no Linux precisa do pacote zstd. Instale com: "
            "sudo apt-get install -y zstd"
        )

    def _install_linux_user_local(self, status_cb: StatusCallback) -> Dict[str, Any]:
        """Download Ollama tarball into ~/.local without root."""
        arch = platform.machine().lower()
        if arch in {"x86_64", "amd64"}:
            arch_tag = "amd64"
        elif arch in {"aarch64", "arm64"}:
            arch_tag = "arm64"
        else:
            return {
                "ok": False,
                "installed": False,
                "error": f"Arquitetura não suportada para install local: {arch}",
                "install_url": self.install_url_for_platform(),
            }
        dest_root = Path(os.path.expanduser("~/.local"))
        bin_dir = dest_root / "bin"
        lib_dir = dest_root / "lib" / "ollama"
        bin_dir.mkdir(parents=True, exist_ok=True)
        if lib_dir.exists():
            shutil.rmtree(lib_dir, ignore_errors=True)
        lib_dir.mkdir(parents=True, exist_ok=True)

        url = f"https://ollama.com/download/ollama-linux-{arch_tag}.tgz"
        # Prefer zst when available (current upstream); fall back to .tgz naming.
        zst_url = f"https://ollama.com/download/ollama-linux-{arch_tag}.tar.zst"
        self._emit(status_cb, "Baixando Ollama para instalação local (~/.local)...")
        tmp = Path(tempfile.mkdtemp(prefix="ollama-install-"))
        try:
            archive = tmp / "ollama.tar.zst"
            try:
                urllib.request.urlretrieve(zst_url, archive)
                use_zst = True
            except Exception:
                archive = tmp / "ollama.tgz"
                urllib.request.urlretrieve(url, archive)
                use_zst = False

            extract_dir = tmp / "extract"
            extract_dir.mkdir()
            if use_zst:
                if not shutil.which("zstd"):
                    return {
                        "ok": False,
                        "installed": False,
                        "error": "zstd ausente — necessário para extrair o pacote Ollama.",
                        "install_url": self.install_url_for_platform(),
                    }
                completed = subprocess.run(
                    f'zstd -d -c "{archive}" | tar -xf - -C "{extract_dir}"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if completed.returncode != 0:
                    return {
                        "ok": False,
                        "installed": False,
                        "error": "Falha ao extrair Ollama (zstd/tar).",
                        "detail": ((completed.stderr or "") + (completed.stdout or ""))[:240],
                    }
            else:
                subprocess.run(
                    ["tar", "-xzf", str(archive), "-C", str(extract_dir)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

            # Official archive layout: bin/ollama + lib/ollama/*
            src_bin = extract_dir / "bin" / "ollama"
            if not src_bin.is_file():
                # Sometimes the binary is at archive root.
                candidates = list(extract_dir.rglob("ollama"))
                src_bin = next((p for p in candidates if p.is_file() and p.name == "ollama"), None)  # type: ignore[assignment]
            if not src_bin or not Path(src_bin).is_file():
                return {
                    "ok": False,
                    "installed": False,
                    "error": "Pacote Ollama baixado sem binário reconhecível.",
                    "install_url": self.install_url_for_platform(),
                }

            target_bin = bin_dir / "ollama"
            shutil.copy2(src_bin, target_bin)
            target_bin.chmod(0o755)

            src_lib = extract_dir / "lib" / "ollama"
            if src_lib.is_dir():
                if lib_dir.exists():
                    shutil.rmtree(lib_dir, ignore_errors=True)
                shutil.copytree(src_lib, lib_dir)

            # Ensure ~/.local/bin is discoverable for this process.
            path_env = os.environ.get("PATH", "")
            if str(bin_dir) not in path_env.split(":"):
                os.environ["PATH"] = f"{bin_dir}:{path_env}"

            if self.is_installed():
                return {
                    "ok": True,
                    "installed": True,
                    "message": "Ollama instalado em ~/.local/bin (sem root).",
                }
            return {
                "ok": False,
                "installed": False,
                "error": "Instalação local concluída, mas ollama não ficou no PATH. Reinicie a plataforma.",
                "install_url": self.install_url_for_platform(),
            }
        except Exception as exc:
            return {
                "ok": False,
                "installed": False,
                "error": f"Falha na instalação local do Ollama: {exc}",
                "install_url": self.install_url_for_platform(),
            }
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _install_linux(self, status_cb: StatusCallback) -> Dict[str, Any]:
        if not shutil.which("curl"):
            return {
                "ok": False,
                "installed": False,
                "error": "curl não encontrado. Instale Ollama manualmente: https://ollama.com/download",
                "install_url": "https://ollama.com/download/linux",
            }

        zstd_err = self._ensure_linux_extract_tools(status_cb)
        if zstd_err and not shutil.which("zstd"):
            # Still try user-local only if zstd somehow appears later; otherwise fail clearly.
            return {
                "ok": False,
                "installed": False,
                "error": zstd_err,
                "install_url": self.install_url_for_platform(),
            }

        # Prefer non-interactive sudo when available (common in cloud/dev VMs).
        if self._can_sudo_n():
            self._emit(status_cb, "Instalando Ollama via script oficial (sudo sem senha)...")
            try:
                completed = subprocess.run(
                    ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sudo -n sh"],
                    capture_output=True,
                    text=True,
                    timeout=INSTALL_TIMEOUT,
                    check=True,
                )
                _ = (completed.stdout or "") + (completed.stderr or "")
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or "").strip()
                lower = detail.lower()
                if "zstd" in lower:
                    hint = " Instale zstd: sudo apt-get install -y zstd"
                elif "password" in lower or "a terminal is required" in lower:
                    hint = " Sem sudo interativo — tentando instalação local..."
                    self._emit(status_cb, hint.strip())
                    local = self._install_linux_user_local(status_cb)
                    if local.get("ok"):
                        return local
                    hint = " Execute no terminal: sudo apt-get install -y zstd && curl -fsSL https://ollama.com/install.sh | sh"
                else:
                    hint = " Tentando instalação local em ~/.local..."
                    self._emit(status_cb, hint.strip())
                    local = self._install_linux_user_local(status_cb)
                    if local.get("ok"):
                        return local
                    hint = " Execute: curl -fsSL https://ollama.com/install.sh | sh"
                return {
                    "ok": False,
                    "installed": False,
                    "error": f"Instalação Linux falhou (exit {exc.returncode}).{hint}",
                    "install_url": self.install_url_for_platform(),
                    "detail": detail[:240] if detail else None,
                }
            except subprocess.TimeoutExpired:
                return {
                    "ok": False,
                    "installed": False,
                    "error": "Timeout ao instalar Ollama no Linux.",
                    "install_url": self.install_url_for_platform(),
                }

            if self._wait_for_binary(status_cb):
                return {"ok": True, "installed": True, "message": "Ollama instalado com sucesso."}

        # No passwordless sudo — try user-local first, then interactive-style script.
        self._emit(status_cb, "Sem sudo sem senha — tentando instalação local do Ollama...")
        local = self._install_linux_user_local(status_cb)
        if local.get("ok"):
            return local

        self._emit(status_cb, "Instalando Ollama via script oficial (pode pedir senha sudo)...")
        try:
            completed = subprocess.run(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                capture_output=True,
                text=True,
                timeout=INSTALL_TIMEOUT,
                check=True,
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            if "password" in output.lower() or "sudo" in output.lower():
                self._emit(status_cb, "Instalação concluída (sudo utilizado).")
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            lower = detail.lower()
            if "zstd" in lower:
                hint = " Instale zstd: sudo apt-get install -y zstd && curl -fsSL https://ollama.com/install.sh | sh"
            elif "password" in lower or "sudo" in lower or "a terminal is required" in lower:
                hint = (
                    " A instalação precisa de sudo no terminal: "
                    "sudo apt-get install -y zstd && curl -fsSL https://ollama.com/install.sh | sh"
                )
            else:
                hint = " Execute no terminal: curl -fsSL https://ollama.com/install.sh | sh"
            return {
                "ok": False,
                "installed": False,
                "error": f"Instalação Linux falhou (exit {exc.returncode}).{hint}",
                "install_url": self.install_url_for_platform(),
                "detail": detail[:240] if detail else None,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "installed": False,
                "error": "Timeout ao instalar Ollama no Linux.",
                "install_url": self.install_url_for_platform(),
            }

        if self._wait_for_binary(status_cb):
            return {"ok": True, "installed": True, "message": "Ollama instalado com sucesso."}
        return {
            "ok": False,
            "installed": False,
            "error": "Ollama instalado, mas não encontrado no PATH. Reinicie a aplicação.",
            "install_url": self.install_url_for_platform(),
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
