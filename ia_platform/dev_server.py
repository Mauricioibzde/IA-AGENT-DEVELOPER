"""Manage per-project npm dev servers for live preview."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


PORT_MIN = 9200
PORT_MAX = 9299
STARTUP_TIMEOUT = 90


class DevServerError(RuntimeError):
    """Raised when dev server startup or npm install fails."""

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr[-1200:]


@dataclass
class DevSession:
    project_id: str
    port: int
    url: str
    script: str
    process: subprocess.Popen[str]


class DevServerManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, DevSession] = {}
        self._last_errors: Dict[str, str] = {}

    def detect_dev_script(self, project_dir: Path) -> Optional[str]:
        package_json = project_dir / "package.json"
        if not package_json.is_file():
            return None
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        scripts = data.get("scripts") if isinstance(data, dict) else None
        if not isinstance(scripts, dict):
            return None
        for name in ("dev", "start", "serve"):
            if name in scripts and str(scripts[name]).strip():
                return name
        return None

    def _npm_available(self) -> bool:
        return shutil.which("npm") is not None

    def _pick_port(self) -> int:
        for port in range(PORT_MIN, PORT_MAX + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        raise DevServerError("Nenhuma porta livre entre 9200-9299")

    @staticmethod
    def _read_process_stderr(process: subprocess.Popen[str]) -> str:
        if not process.stderr:
            return ""
        try:
            if process.poll() is None:
                return ""
            return (process.stderr.read() or "")[-1200:]
        except OSError:
            return ""

    def _cleanup_session(self, project_id: str, *, record_error: bool = False) -> None:
        session = self._sessions.pop(project_id, None)
        if not session:
            return
        stderr = ""
        if record_error or session.process.poll() is not None:
            stderr = self._read_process_stderr(session.process)
            if stderr:
                self._last_errors[project_id] = stderr
        if session.process.poll() is None:
            session.process.terminate()
            try:
                session.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                session.process.kill()

    def _wait_for_http(self, url: str, timeout: float = STARTUP_TIMEOUT) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status < 500:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.5)
        return False

    def _ensure_dependencies(self, project_dir: Path) -> None:
        if (project_dir / "node_modules").exists():
            return
        if not self._npm_available():
            raise DevServerError("npm não encontrado — instale Node.js")
        try:
            completed = subprocess.run(
                ["npm", "install"],
                cwd=str(project_dir),
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or exc.stdout or "")[-1200:]
            raise DevServerError(f"npm install falhou (exit {exc.returncode})", stderr) from exc
        except subprocess.TimeoutExpired as exc:
            raise DevServerError("npm install excedeu o tempo limite (5 min)") from exc
        if completed.stderr and "ERR!" in completed.stderr:
            self._last_errors[str(project_dir)] = completed.stderr[-800:]

    def status(self, project_id: str, project_dir: Path) -> Dict[str, object]:
        with self._lock:
            session = self._sessions.get(project_id)
            if session and session.process.poll() is not None:
                self._cleanup_session(project_id, record_error=True)
                session = None
            script = self.detect_dev_script(project_dir)
            return {
                "npm_available": self._npm_available(),
                "has_dev_script": script is not None,
                "script": script,
                "running": session is not None,
                "port": session.port if session else None,
                "url": session.url if session else None,
                "last_error": self._last_errors.get(project_id),
            }

    def start(self, project_id: str, project_dir: Path, install: bool = True) -> Dict[str, object]:
        if not project_dir.is_dir():
            raise FileNotFoundError("Projeto não encontrado")
        script = self.detect_dev_script(project_dir)
        if not script:
            raise DevServerError("Este projeto não tem script dev/start no package.json")
        if not self._npm_available():
            raise DevServerError("npm não encontrado — instale Node.js para preview ao vivo")

        with self._lock:
            existing = self._sessions.get(project_id)
            if existing and existing.process.poll() is None:
                self._last_errors.pop(project_id, None)
                return {
                    "ok": True,
                    "running": True,
                    "port": existing.port,
                    "url": existing.url,
                    "script": existing.script,
                    "message": "Servidor já estava rodando",
                }
            self._cleanup_session(project_id)

        if install:
            self._ensure_dependencies(project_dir)

        port = self._pick_port()
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["BROWSER"] = "none"
        env["HOST"] = "127.0.0.1"

        cmd = ["npm", "run", script, "--", "--port", str(port), "--host", "127.0.0.1"]
        process = subprocess.Popen(
            cmd,
            cwd=str(project_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        url = f"http://127.0.0.1:{port}/"
        if not self._wait_for_http(url):
            stderr = self._read_process_stderr(process)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                stderr = stderr or self._read_process_stderr(process)
            with self._lock:
                self._sessions.pop(project_id, None)
                if stderr:
                    self._last_errors[project_id] = stderr
            raise DevServerError("Servidor dev não respondeu a tempo.", stderr)

        session = DevSession(project_id=project_id, port=port, url=url, script=script, process=process)
        with self._lock:
            self._sessions[project_id] = session
            self._last_errors.pop(project_id, None)

        return {
            "ok": True,
            "running": True,
            "port": port,
            "url": url,
            "script": script,
            "message": f"npm run {script} rodando",
        }

    def stop(self, project_id: str) -> Dict[str, object]:
        with self._lock:
            self._cleanup_session(project_id)
        return {"ok": True, "running": False}

    def stop_all(self) -> None:
        with self._lock:
            for project_id in list(self._sessions):
                self._cleanup_session(project_id)


dev_manager = DevServerManager()
