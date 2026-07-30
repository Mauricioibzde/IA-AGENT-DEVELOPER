"""Subprocess bridge to the Node Visual Engine CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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


def run_cli(payload: Dict[str, Any], *, timeout: int = 180) -> Dict[str, Any]:
    if not node_available():
        raise VisualEngineBridgeError("Node Visual Engine CLI not available")
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
    # CLI prints one JSON object on stdout
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
