"""Subprocess bridge to the Node Visual Engine CLI.

Uses a persistent ``node src/cli.js --serve`` worker so Chromium stays warm
across compares (critical for correction-loop latency).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
NODE_PKG = REPO_ROOT / "visual_engine"
CLI = NODE_PKG / "src" / "cli.js"


class VisualEngineBridgeError(RuntimeError):
    pass


def node_available() -> bool:
    return shutil.which("node") is not None and CLI.is_file()


def ensure_node_deps() -> None:
    """Install npm deps once if node_modules missing."""
    nm = NODE_PKG / "node_modules"
    if nm.is_dir():
        return
    if not shutil.which("npm"):
        raise VisualEngineBridgeError("npm not found — install Node.js 18+ to use Visual Engine")
    proc = subprocess.run(
        ["npm", "install", "--omit=dev"],
        cwd=str(NODE_PKG),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        raise VisualEngineBridgeError(f"npm install failed: {proc.stderr[-800:] or proc.stdout[-800:]}")


class _CliWorker:
    """Long-lived Node CLI process (NDJSON request/response)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen[str]] = None

    def _alive(self) -> bool:
        return bool(self._proc and self._proc.poll() is None)

    def _start(self) -> None:
        if self._alive():
            return
        ensure_node_deps()
        env = os.environ.copy()
        self._proc = subprocess.Popen(
            ["node", str(CLI), "--serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(NODE_PKG),
            env=env,
        )
        # Wait briefly for serve banner / readiness (best-effort).
        time.sleep(0.15)
        if not self._alive():
            err = ""
            try:
                err = (self._proc.stderr.read() if self._proc and self._proc.stderr else "") or ""
            except Exception:
                pass
            raise VisualEngineBridgeError(f"visual CLI worker failed to start: {err[-500:]}")

    def request(self, payload: Dict[str, Any], *, timeout: int = 180) -> Dict[str, Any]:
        with self._lock:
            self._start()
            assert self._proc and self._proc.stdin and self._proc.stdout
            line = json.dumps(payload, ensure_ascii=False)
            try:
                self._proc.stdin.write(line + "\n")
                self._proc.stdin.flush()
            except BrokenPipeError as exc:
                self._kill()
                raise VisualEngineBridgeError("visual CLI worker pipe broken") from exc

            # Read one response line with timeout via reader thread.
            holder: Dict[str, Any] = {}

            def _read() -> None:
                try:
                    holder["line"] = self._proc.stdout.readline() if self._proc and self._proc.stdout else ""
                except Exception as exc:  # noqa: BLE001
                    holder["error"] = exc

            reader = threading.Thread(target=_read, name="visual-cli-read", daemon=True)
            reader.start()
            reader.join(max(1.0, float(timeout)))
            if reader.is_alive():
                self._kill()
                raise VisualEngineBridgeError(f"visual CLI timed out after {timeout}s")
            if "error" in holder:
                self._kill()
                raise VisualEngineBridgeError(f"visual CLI read failed: {holder['error']}")
            text = str(holder.get("line") or "").strip()
            if not text:
                err = ""
                try:
                    if self._proc and self._proc.stderr:
                        # Non-blocking-ish: may be empty
                        pass
                except Exception:
                    pass
                self._kill()
                raise VisualEngineBridgeError(f"visual CLI empty output {err}")
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise VisualEngineBridgeError(f"Invalid CLI JSON: {text[:400]}") from exc
            if not data.get("ok", False):
                raise VisualEngineBridgeError(str(data.get("error") or "CLI failed"))
            return data

    def _kill(self) -> None:
        proc = self._proc
        self._proc = None
        if not proc:
            return
        try:
            if proc.poll() is None:
                try:
                    if proc.stdin:
                        proc.stdin.write(json.dumps({"op": "shutdown"}) + "\n")
                        proc.stdin.flush()
                except Exception:
                    pass
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
        except Exception:
            pass


_WORKER = _CliWorker()


def run_cli(payload: Dict[str, Any], *, timeout: int = 180) -> Dict[str, Any]:
    if not node_available():
        raise VisualEngineBridgeError("Node Visual Engine CLI not available")
    # One-shot fallback if worker fails (e.g. tests without long-lived node).
    try:
        return _WORKER.request(payload, timeout=timeout)
    except VisualEngineBridgeError:
        return _run_cli_oneshot(payload, timeout=timeout)


def _run_cli_oneshot(payload: Dict[str, Any], *, timeout: int = 180) -> Dict[str, Any]:
    ensure_node_deps()
    env = os.environ.copy()
    proc = subprocess.run(
        ["node", str(CLI)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(NODE_PKG),
        env=env,
        check=False,
    )
    text = (proc.stdout or "").strip()
    if not text:
        raise VisualEngineBridgeError(proc.stderr[-1000:] or f"CLI empty output (code {proc.returncode})")
    last_line = text.splitlines()[-1]
    try:
        data = json.loads(last_line)
    except json.JSONDecodeError as exc:
        raise VisualEngineBridgeError(f"Invalid CLI JSON: {last_line[:400]}") from exc
    if not data.get("ok", False):
        raise VisualEngineBridgeError(str(data.get("error") or "CLI failed"))
    return data


def ping() -> Dict[str, Any]:
    return run_cli({"op": "ping"}, timeout=30)
