"""Local web platform server for app generation."""

from __future__ import annotations

import argparse
import json
import mimetypes
import platform
import re
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ia_platform.conversations import append_message, clear_messages, format_conversation_context, load_messages
from ia_platform.deploy import deploy_project
from ia_platform.dev_server import DevServerError, dev_manager
from ia_platform.hardware import detect_hardware
from ia_platform.model_catalog import (
    recommend_models,
    recommend_setup_model,
    resolve_model_for_chat,
    resolve_model_for_run,
    resolve_models_for_run,
)
from ia_platform.ollama_models import OllamaModelManager
from ia_platform.ollama_service import ollama_service
from ia_platform.project_templates import PROJECT_TEMPLATES, get_template_files
from ia_platform.run_history import load_runs, record_run
from ia_platform.run_manager import run_manager

STATIC = ROOT / "static"
PROJECTS_ROOT = ROOT.parent / "projects"
DEFAULT_WORKSPACE = ROOT.parent / "sandbox"
PLATFORM_VERSION = 2
IGNORE_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".agent", ".pytest_cache"}

_HARDWARE_CACHE: Optional[tuple[float, Dict[str, Any]]] = None
_HARDWARE_CACHE_TTL = 60.0


def _cached_hardware() -> Dict[str, Any]:
    global _HARDWARE_CACHE
    now = time.time()
    if _HARDWARE_CACHE and now - _HARDWARE_CACHE[0] < _HARDWARE_CACHE_TTL:
        return _HARDWARE_CACHE[1]
    hw = detect_hardware()
    _HARDWARE_CACHE = (now, hw)
    return hw

def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", name.strip())[:64]
    return cleaned or "project"


def _project_path(project_id: str) -> Path:
    safe = _safe_name(project_id)
    path = (PROJECTS_ROOT / safe).resolve()
    if not str(path).startswith(str(PROJECTS_ROOT.resolve())):
        raise ValueError("Invalid project id")
    return path


def _resolve_workspace(raw: str | None) -> Path:
    """Resolve a workspace path, confined to projects/ or sandbox/."""
    if raw and str(raw).startswith("projects/"):
        return _project_path(str(raw).split("/", 1)[1])

    projects_root = PROJECTS_ROOT.resolve()
    sandbox_root = DEFAULT_WORKSPACE.resolve()

    if not raw or str(raw).strip() in {"", "sandbox", "sandbox/"}:
        DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)
        return sandbox_root

    path = Path(str(raw).strip())
    if path.is_absolute():
        raise ValueError("Absolute workspace paths are not allowed; use projects/<id> or sandbox/")

    candidate = (ROOT.parent / path).resolve()
    for root in (projects_root, sandbox_root):
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise ValueError("Workspace must be under projects/ or sandbox/")


def _project_has_dev_script(project_dir: Path) -> bool:
    return dev_manager.detect_dev_script(project_dir) is not None


def _should_skip_path(path: Path) -> bool:
    return any(part in IGNORE_DIRS or part.startswith(".") for part in path.parts)


def _list_files(base: Path, rel: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
    if recursive:
        items: List[Dict[str, Any]] = []
        if not base.exists():
            return items
        for entry in sorted(base.rglob("*"), key=lambda p: str(p).lower()):
            if _should_skip_path(entry.relative_to(base)):
                continue
            entry_rel = str(entry.relative_to(base)).replace("\\", "/")
            if entry.is_dir():
                items.append({"name": entry.name, "path": entry_rel, "type": "dir"})
            else:
                items.append({"name": entry.name, "path": entry_rel, "type": "file", "size": entry.stat().st_size})
        return items

    target = base / rel if rel else base
    if not target.exists() or not target.is_dir():
        return []
    items = []
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if entry.name in IGNORE_DIRS or entry.name.startswith("."):
            continue
        entry_rel = str(entry.relative_to(base)).replace("\\", "/")
        if entry.is_dir():
            items.append({"name": entry.name, "path": entry_rel, "type": "dir"})
        else:
            items.append({"name": entry.name, "path": entry_rel, "type": "file", "size": entry.stat().st_size})
    return items


def _apply_template(project_dir: Path, template: str) -> None:
    files = get_template_files(template, project_dir.name)
    for rel_path, content in files.items():
        target = project_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _parse_project_route(path: str) -> Tuple[Optional[str], Optional[str]]:
    parts = path.strip("/").split("/")
    if len(parts) >= 4 and parts[0] == "api" and parts[1] == "projects":
        return parts[2], "/".join(parts[3:])
    return None, None


def _project_id_from_workspace(workspace: Path) -> Optional[str]:
    try:
        rel = workspace.resolve().relative_to(PROJECTS_ROOT.resolve())
        if rel.parts:
            return rel.parts[0]
    except ValueError:
        pass
    return None


class PlatformHandler(BaseHTTPRequestHandler):
    server_version = "ForgePlatform/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("[platform] %s - %s\n" % (self.address_string(), format % args))

    def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            return self._handle_health()
        if path == "/api/setup/status":
            return self._handle_setup_status()
        if path == "/api/system/hardware":
            return self._handle_hardware()
        if path == "/api/models/recommendations":
            return self._handle_model_recommendations()
        if path == "/api/models/installed":
            return self._handle_models_installed()
        if path == "/api/projects":
            return self._handle_list_projects()
        if path.startswith("/preview/"):
            rest = path[len("/preview/") :].lstrip("/")
            if rest:
                project_id, _, file_path = rest.partition("/")
                return self._serve_project_file(project_id, file_path or "index.html")
        if path.startswith("/api/projects/") and path.endswith("/files"):
            project_id = path.split("/")[3]
            recursive = qs.get("recursive", ["0"])[0] in {"1", "true", "yes"}
            return self._handle_list_project_files(project_id, recursive=recursive)
        if path.startswith("/api/projects/") and "/file" in path:
            parts = path.split("/")
            if len(parts) >= 5 and parts[4] == "file":
                project_id = parts[3]
                file_path = qs.get("path", [""])[0]
                return self._handle_read_file(project_id, file_path)
        project_id, sub = _parse_project_route(path)
        if project_id and sub == "chat":
            return self._handle_get_chat(project_id)
        if project_id and sub == "dev/status":
            return self._handle_dev_status(project_id)
        if project_id and sub == "runs":
            return self._handle_get_runs(project_id)
        if project_id and sub == "search":
            return self._handle_project_search(project_id, qs)
        if path in {"/", "/index.html"}:
            return self._serve_file(STATIC / "index.html")
        if path.startswith("/static/"):
            return self._serve_file(STATIC / path[len("/static/"):])
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/run":
            return self._handle_run()
        if path == "/api/run/stream":
            return self._handle_run_stream()
        if path == "/api/chat/stream":
            return self._handle_chat_stream()
        if path == "/api/run/cancel":
            return self._handle_run_cancel()
        if path == "/api/projects":
            return self._handle_create_project()
        if path == "/api/models/pull/stream":
            return self._handle_model_pull_stream()
        if path == "/api/ollama/ensure":
            return self._handle_ollama_ensure()
        if path == "/api/ollama/setup/stream":
            return self._handle_ollama_setup_stream()
        if path == "/api/setup/stream":
            return self._handle_full_setup_stream()
        if path == "/api/setup/status":
            return self._handle_setup_status()
        project_id, sub = _parse_project_route(path)
        if project_id and sub == "chat":
            return self._handle_post_chat(project_id)
        if project_id and sub == "dev/start":
            return self._handle_dev_start(project_id)
        if project_id and sub == "dev/stop":
            return self._handle_dev_stop(project_id)
        if project_id and sub == "deploy":
            return self._handle_deploy(project_id)
        self._send_json(404, {"error": "not found"})

    def _ollama_host(self) -> str:
        from local_agent.config import AgentConfig

        return AgentConfig.from_args(PROJECTS_ROOT, no_memory=True).ollama_host

    def _ollama_manager(self) -> OllamaModelManager:
        return OllamaModelManager(self._ollama_host())

    def _ensure_ollama_online(self, auto_install: bool = True) -> Optional[Dict[str, Any]]:
        """Try to reach Ollama; install/start local daemon when possible."""
        from local_agent.config import AgentConfig
        from local_agent.ollama_client import OllamaClient

        host = self._ollama_host()
        cfg = AgentConfig.from_args(PROJECTS_ROOT, no_memory=True)
        if OllamaClient(cfg).check_available(timeout=2):
            return None
        result = ollama_service.ensure_running(host, auto_install=auto_install)
        if result.get("ok"):
            return None
        return result

    def _ollama_setup_auto_install(self, data: Dict[str, Any]) -> bool:
        if "install" not in data:
            return True
        return bool(data.get("install"))

    def _handle_ollama_ensure(self) -> None:
        from local_agent.config import AgentConfig
        from local_agent.ollama_client import OllamaClient

        data = self._read_json()
        auto_install = self._ollama_setup_auto_install(data)
        host = self._ollama_host()
        cfg = AgentConfig.from_args(PROJECTS_ROOT, no_memory=True)
        if OllamaClient(cfg).check_available(timeout=2):
            return self._send_json(
                200,
                {
                    "ok": True,
                    "ollama": True,
                    "started": False,
                    "installed": True,
                    "message": "Ollama já está online.",
                },
            )
        result = ollama_service.ensure_running(host, auto_install=auto_install)
        status = 200 if result.get("ok") else 503
        return self._send_json(status, result)

    def _handle_ollama_setup_stream(self) -> None:
        data = self._read_json()
        auto_install = self._ollama_setup_auto_install(data)
        host = self._ollama_host()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def emit(payload: Dict[str, Any]) -> None:
            self._send_sse(payload)

        def status_cb(message: str) -> None:
            emit({"type": "status", "message": message})

        try:
            emit({"type": "started"})
            if ollama_service.is_api_ready(host):
                emit({"type": "status", "message": "Ollama já está online."})
                emit({"type": "done", "ok": True, "ollama": True, "installed": True, "started": False})
                return

            result = ollama_service.ensure_running(host, auto_install=auto_install, status_cb=status_cb)
            emit({"type": "done", **result})
        except Exception as exc:
            emit({"type": "error", "error": str(exc)})
            emit({"type": "done", "ok": False, "ollama": False, "error": str(exc)})

    def _handle_setup_status(self) -> None:
        from local_agent.config import AgentConfig
        from local_agent.ollama_client import OllamaClient

        cfg = AgentConfig.from_args(PROJECTS_ROOT, no_memory=True)
        client = OllamaClient(cfg)
        ollama_online = client.check_available(timeout=2)
        installed = client.list_models() if ollama_online else []
        hw = _cached_hardware()
        setup_model = recommend_setup_model(hw, installed)
        mgr = self._ollama_manager()
        has_setup_model = mgr.has_model(setup_model)
        ready = ollama_online and (has_setup_model or bool(installed))
        system = platform.system()
        auto_install = system in {"Windows", "Linux", "Darwin"}

        self._send_json(
            200,
            {
                "ollama_online": ollama_online,
                "ollama_installed": ollama_service.is_installed(),
                "models_installed": installed,
                "recommended_model": setup_model,
                "setup_complete": ready,
                "hardware_tier": hw.get("tier"),
                "has_gpu": bool(hw.get("has_gpu") or hw.get("gpus")),
                "platform": system.lower(),
                "auto_install_supported": auto_install,
                "install_url": ollama_service.install_url_for_platform(),
                "needs_ollama": not ollama_online,
                "needs_model": ollama_online and not has_setup_model and not installed,
            },
        )

    def _handle_full_setup_stream(self) -> None:
        data = self._read_json()
        auto_install = self._ollama_setup_auto_install(data)
        pull_recommended = bool(data.get("pull_recommended", True))
        host = self._ollama_host()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def emit(payload: Dict[str, Any]) -> None:
            self._send_sse(payload)

        def phase(phase_id: str, message: str, percent: int, **extra: Any) -> None:
            emit({"type": "phase", "phase": phase_id, "message": message, "percent": percent, **extra})

        try:
            phase("check", "Verificando ambiente...", 5)

            if not ollama_service.is_api_ready(host):

                def ollama_status(message: str) -> None:
                    lower = message.lower()
                    if "instal" in lower or "winget" in lower or "download" in lower:
                        phase("install", message, 22)
                    else:
                        phase("start", message, 35)

                ollama_result = ollama_service.ensure_running(
                    host,
                    auto_install=auto_install,
                    status_cb=ollama_status,
                )
                if not ollama_result.get("ok"):
                    emit({"type": "done", "ok": False, **ollama_result})
                    return
                if ollama_result.get("started") or "instal" in str(ollama_result.get("message", "")).lower():
                    phase("install", ollama_result.get("message") or "Ollama instalado.", 38, installed=True)
                else:
                    phase("install", "Ollama já estava instalado.", 32, skipped=True)
            else:
                phase("install", "Ollama já instalado.", 32, skipped=True)

            phase("start", "Serviço Ollama online.", 45)

            hw = _cached_hardware()
            mgr = self._ollama_manager()
            installed = mgr.list_names()
            setup_model = recommend_setup_model(hw, installed)
            gpu_note = "GPU detectada" if hw.get("has_gpu") or hw.get("gpus") else "modo CPU (sem GPU)"
            phase(
                "hardware",
                f"Recomendado: {setup_model} — {gpu_note}, tier {hw.get('tier', '?')}.",
                52,
                model=setup_model,
                hardware=hw.get("tier"),
            )

            needs_pull = pull_recommended and not mgr.has_model(setup_model)
            if needs_pull:

                def pull_event(event: Dict[str, Any]) -> None:
                    if event.get("type") != "progress":
                        return
                    pct = event.get("percent")
                    overall = 55 + int(pct * 0.38) if pct is not None else 58
                    msg = event.get("status") or f"Baixando {setup_model}..."
                    if pct is not None:
                        msg = f"Baixando {setup_model}... {pct}%"
                    emit({"type": "progress", "phase": "model", "message": msg, "percent": overall})

                phase("model", f"Iniciando download de {setup_model} (~pode demorar)...", 55, model=setup_model)
                pull_result = mgr.pull(setup_model, on_event=pull_event)
                if not pull_result.get("ok"):
                    emit(
                        {
                            "type": "done",
                            "ok": False,
                            "error": pull_result.get("error") or f"Falha ao baixar {setup_model}",
                            "model": setup_model,
                        }
                    )
                    return
                phase("model", f"Modelo {setup_model} instalado.", 93, model=setup_model)
            elif mgr.has_model(setup_model):
                phase("model", f"Modelo {setup_model} já instalado.", 88, model=setup_model, skipped=True)
            else:
                phase("model", "Nenhum modelo baixado (pull desativado).", 88, skipped=True)

            installed = mgr.list_names()
            phase("config", f"Configurando {setup_model} como modelo padrão.", 97, model=setup_model)
            emit(
                {
                    "type": "done",
                    "ok": True,
                    "ollama": True,
                    "installed": True,
                    "model": setup_model,
                    "models": installed,
                    "message": "Ambiente configurado — pronto para usar!",
                    "percent": 100,
                }
            )
        except Exception as exc:
            emit({"type": "error", "error": str(exc)})
            emit({"type": "done", "ok": False, "error": str(exc)})

    def _handle_health(self) -> None:
        from local_agent.config import AgentConfig
        from local_agent.ollama_client import OllamaClient

        cfg = AgentConfig.from_args(PROJECTS_ROOT, no_memory=True)
        client = OllamaClient(cfg)
        ollama_ok = client.check_available(timeout=2)
        models = client.list_models() if ollama_ok else []
        recommended_name = None
        if ollama_ok:
            hw = _cached_hardware()
            recommended_name = recommend_setup_model(hw, models)
        self._send_json(
            200,
            {
                "ok": True,
                "agent": True,
                "ollama": ollama_ok,
                "models": models[:20],
                "recommended_model": recommended_name,
                "projects_root": str(PROJECTS_ROOT),
                "platform_version": PLATFORM_VERSION,
                "features": {
                    "ollama_setup_stream": True,
                    "ollama_auto_install": True,
                    "full_setup_stream": True,
                },
            },
        )

    def _handle_hardware(self) -> None:
        return self._send_json(200, {"hardware": detect_hardware()})

    def _handle_models_installed(self) -> None:
        mgr = self._ollama_manager()
        return self._send_json(200, {"models": mgr.list_installed()})

    def _handle_model_recommendations(self) -> None:
        hw = detect_hardware()
        installed = self._ollama_manager().list_names()
        return self._send_json(200, recommend_models(hw, installed))

    def _handle_model_pull_stream(self) -> None:
        data = self._read_json()
        model = str(data.get("model") or data.get("name") or "").strip()
        if not model:
            return self._send_json(400, {"error": "model is required"})

        from local_agent.config import AgentConfig
        from local_agent.ollama_client import OllamaClient

        cfg = AgentConfig.from_args(PROJECTS_ROOT, no_memory=True)
        offline = self._ensure_ollama_online()
        if offline:
            return self._send_json(
                503,
                {
                    "error": offline.get("error")
                    or "Ollama offline. Instale ou reinicie o Ollama.",
                    "ollama_offline": True,
                    "installed": offline.get("installed", True),
                    "install_url": offline.get("install_url"),
                },
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        mgr = self._ollama_manager()

        def emit(payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.wfile.write(b"data: " + body + b"\n\n")
            self.wfile.flush()

        try:
            emit({"type": "started", "model": model})
            result = mgr.pull(model, on_event=emit)
            emit({"type": "done", **result})
        except Exception as exc:
            emit({"type": "error", "error": str(exc)})

    def _handle_list_projects(self) -> None:
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        projects = []
        for entry in sorted(PROJECTS_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            files = list(entry.rglob("*"))
            file_count = sum(1 for f in files if f.is_file() and not any(p in IGNORE_DIRS for p in f.parts))
            projects.append(
                {
                    "id": entry.name,
                    "name": entry.name,
                    "path": f"projects/{entry.name}",
                    "files": file_count,
                    "updated": entry.stat().st_mtime,
                }
            )
        self._send_json(200, {"projects": projects})

    def _handle_create_project(self) -> None:
        data = self._read_json()
        name = _safe_name(str(data.get("name") or "novo-projeto"))
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        project_dir = PROJECTS_ROOT / name
        if project_dir.exists():
            # append suffix
            for i in range(2, 100):
                candidate = PROJECTS_ROOT / f"{name}-{i}"
                if not candidate.exists():
                    project_dir = candidate
                    name = candidate.name
                    break
        project_dir.mkdir(parents=True, exist_ok=True)
        template = str(data.get("template") or "blank")
        readme = f"# {name}\n\nGerado pela plataforma IA Agent Developer.\n"
        known = set(PROJECT_TEMPLATES) | {"react"}
        if template == "blank" or template not in known:
            (project_dir / "README.md").write_text(readme, encoding="utf-8")
        else:
            _apply_template(project_dir, template)
            readme_path = project_dir / "README.md"
            if not readme_path.exists():
                readme_path.write_text(readme, encoding="utf-8")
        self._send_json(
            201,
            {
                "id": name,
                "name": name,
                "path": f"projects/{name}",
                "template": template,
                "has_dev_script": _project_has_dev_script(project_dir),
            },
        )

    def _handle_list_project_files(self, project_id: str, recursive: bool = False) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        if not base.exists():
            return self._send_json(404, {"error": "project not found"})
        self._send_json(200, {"project": project_id, "files": _list_files(base, recursive=recursive)})

    def _serve_project_file(self, project_id: str, file_path: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        target = (base / file_path).resolve()
        try:
            target.relative_to(base.resolve())
        except ValueError:
            return self._send_json(403, {"error": "access denied"})
        if not target.is_file():
            return self._send_json(404, {"error": "file not found"})
        content = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_read_file(self, project_id: str, file_path: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        target = (base / file_path).resolve()
        try:
            target.relative_to(base.resolve())
        except ValueError:
            return self._send_json(403, {"error": "access denied"})
        if not target.is_file():
            return self._send_json(404, {"error": "file not found"})
        if target.stat().st_size > 500_000:
            return self._send_json(413, {"error": "file too large"})
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return self._send_json(415, {"error": "binary file"})
        self._send_json(200, {"path": file_path, "content": content})

    def _handle_get_chat(self, project_id: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        if not base.exists():
            return self._send_json(404, {"error": "project not found"})
        return self._send_json(200, {"project": project_id, "messages": load_messages(base)})

    def _handle_post_chat(self, project_id: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        if not base.exists():
            return self._send_json(404, {"error": "project not found"})
        data = self._read_json()
        if data.get("clear"):
            clear_messages(base)
            return self._send_json(200, {"ok": True, "messages": []})
        role = str(data.get("role", "")).strip()
        text = str(data.get("text", "")).strip()
        if not role or not text:
            return self._send_json(400, {"error": "role and text are required"})
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else None
        messages = append_message(base, role, text, meta=meta)
        return self._send_json(201, {"ok": True, "messages": messages})

    def _handle_get_runs(self, project_id: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        if not base.exists():
            return self._send_json(404, {"error": "project not found"})
        runs = load_runs(base, limit=30)
        return self._send_json(200, {"project": project_id, "runs": runs})

    def _handle_project_search(self, project_id: str, qs: Dict[str, List[str]]) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        if not base.exists():
            return self._send_json(404, {"error": "project not found"})
        query = str(qs.get("q", [""])[0]).strip()
        if not query:
            return self._send_json(400, {"error": "q is required"})

        from local_agent.project_index import ProjectIndex

        index = ProjectIndex(base)
        index.build()
        matches = index.search_relevant(query, limit=15)
        return self._send_json(
            200,
            {
                "project": project_id,
                "query": query,
                "matches": [
                    {
                        "path": f.path,
                        "language": f.language,
                        "symbols": f.symbols[:8],
                        "size": f.size,
                    }
                    for f in matches
                ],
            },
        )

    def _handle_dev_status(self, project_id: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        if not base.exists():
            return self._send_json(404, {"error": "project not found"})
        status = dev_manager.status(project_id, base)
        return self._send_json(200, {"project": project_id, **status})

    def _handle_dev_start(self, project_id: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        data = self._read_json()
        install = bool(data.get("install", True))
        try:
            result = dev_manager.start(project_id, base, install=install)
            return self._send_json(200, {"project": project_id, **result})
        except DevServerError as exc:
            return self._send_json(500, {"error": str(exc), "stderr": exc.stderr})
        except Exception as exc:
            return self._send_json(500, {"error": str(exc)})

    def _handle_dev_stop(self, project_id: str) -> None:
        result = dev_manager.stop(project_id)
        return self._send_json(200, {"project": project_id, **result})

    def _handle_deploy(self, project_id: str) -> None:
        try:
            base = _project_path(project_id)
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        if not base.exists():
            return self._send_json(404, {"error": "project not found"})
        result = deploy_project(base, project_id)
        return self._send_json(200, {"project": project_id, **result})

    def _build_agent_config(self, data: Dict[str, Any], workspace: Path, models: Dict[str, str]):
        from local_agent.config import AgentConfig

        cfg = AgentConfig.from_args(
            workspace,
            model=models["coder"],
            planner_model=models["planner"],
            reflection_model=models["reflection"],
            max_steps=int(data.get("max_steps") or 12),
            dry_run=bool(data.get("dry_run")),
            plan_only=bool(data.get("plan_only")),
            verbose=True,
        )
        return cfg

    def _prepare_run(self, data: Dict[str, Any], workspace: Path) -> tuple[Dict[str, str], str, Optional[Dict[str, Any]]]:
        """Resolve models, build conversation context, preflight availability."""
        offline = self._ensure_ollama_online()
        if offline:
            return {}, "", {
                "error": offline.get("error")
                or "Ollama offline. A plataforma tentou iniciar automaticamente sem sucesso.",
                "ollama_offline": True,
                "installed": offline.get("installed", True),
                "install_url": offline.get("install_url"),
            }

        mgr = self._ollama_manager()
        installed = mgr.list_names()
        hardware = _cached_hardware()
        models = resolve_models_for_run(data.get("model"), installed, hardware)
        coder = models["coder"]

        if not installed:
            primary = recommend_models(hardware, installed).get("primary", {})
            suggested = primary.get("ollama_name") or coder
            return models, "", {
                "error": f"Nenhum modelo instalado. Baixe '{suggested}' em Modelos IA ou execute: ollama pull {suggested}",
                "model": suggested,
                "missing_model": True,
                "pull_available": True,
                "recommended": primary,
            }

        for role, name in models.items():
            if not mgr.has_model(name):
                return models, "", {
                    "error": f"Modelo '{name}' ({role}) não está instalado. Baixe em Modelos IA.",
                    "model": name,
                    "missing_model": True,
                    "pull_available": True,
                    "recommended": recommend_models(hardware, installed).get("primary"),
                }

        messages = load_messages(workspace)
        if messages and messages[-1].get("role") == "user":
            prior = messages[:-1]
        else:
            prior = messages
        conversation = format_conversation_context(prior, limit=10)
        return models, conversation, None

    def _preflight_status(self, preflight_error: Dict[str, Any]) -> int:
        if preflight_error.get("ollama_offline"):
            return 503
        return 400

    def _finalize_run(
        self,
        workspace: Path,
        project_id: Optional[str],
        report,
        *,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        rendered = report.render()
        chat_summary = self._chat_facing_summary(report)
        if project_id:
            append_message(
                workspace,
                "agent",
                chat_summary,
                meta={
                    "status": report.status.value,
                    "created_files": report.created_files,
                    "modified_files": report.modified_files,
                    "run_id": run_id,
                    "full_report": True,
                },
            )
            record_run(
                workspace,
                goal=report.goal,
                status=report.status.value,
                report=rendered,
                created_files=report.created_files,
                modified_files=report.modified_files,
                run_id=run_id,
            )
        return {
            "ok": True,
            "status": report.status.value,
            "summary": chat_summary,
            "report": rendered,
            "workspace": str(workspace),
            "created_files": report.created_files,
            "modified_files": report.modified_files,
            "run_id": run_id,
            "completed_tasks": list(getattr(report, "completed_tasks", []) or []),
        }

    @staticmethod
    def _chat_facing_summary(report) -> str:
        summary = str(getattr(report, "summary", "") or "").strip() or "Execução concluída."
        status = getattr(getattr(report, "status", None), "value", "") or ""
        created = list(getattr(report, "created_files", []) or [])
        modified = list(getattr(report, "modified_files", []) or [])
        tasks = list(getattr(report, "completed_tasks", []) or [])
        sections = [summary]
        if status:
            sections.append(f"Status: **{status}**")
        if tasks:
            bullet = "\n".join(f"- {task}" for task in tasks[:6])
            sections.append(f"**Tarefas concluídas**\n{bullet}")
        if created:
            bullet = "\n".join(f"- `{path}`" for path in created[:8])
            sections.append(f"**Arquivos criados**\n{bullet}")
        if modified:
            bullet = "\n".join(f"- `{path}`" for path in modified[:8])
            sections.append(f"**Arquivos alterados**\n{bullet}")
        sections.append("_Detalhes técnicos estão no painel Relatório._")
        return "\n\n".join(sections)

    def _send_sse(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.wfile.write(b"data: " + body + b"\n\n")
        self.wfile.flush()

    def _handle_run_cancel(self) -> None:
        data = self._read_json()
        run_id = str(data.get("run_id") or "").strip()
        if not run_id:
            return self._send_json(400, {"error": "run_id is required"})
        cancelled = run_manager.cancel(run_id)
        return self._send_json(200, {"ok": True, "cancelled": cancelled, "run_id": run_id})

    def _chat_history_for_ollama(self, workspace: Path, limit: int = 16) -> list:
        messages = load_messages(workspace)
        if messages and messages[-1].get("role") == "user":
            messages = messages[:-1]
        history = []
        for msg in messages[-limit:]:
            role = str(msg.get("role") or "")
            text = str(msg.get("text") or "").strip()
            if not text:
                continue
            if role == "user":
                history.append({"role": "user", "content": text[:4000]})
            elif role == "agent":
                history.append({"role": "assistant", "content": text[:4000]})
        return history

    def _handle_chat_stream(self) -> None:
        """Fast conversational mode — no planner/tools loop."""
        data = self._read_json()
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return self._send_json(400, {"error": "prompt is required"})

        try:
            workspace = _resolve_workspace(data.get("workspace") or data.get("project_path"))
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        workspace.mkdir(parents=True, exist_ok=True)
        project_id = _project_id_from_workspace(workspace)

        models, _conversation, preflight_error = self._prepare_run(data, workspace)
        if preflight_error:
            return self._send_json(self._preflight_status(preflight_error), preflight_error)

        requested = str(data.get("model") or "").strip()
        if not requested:
            mgr = self._ollama_manager()
            models = {
                **models,
                "coder": resolve_model_for_chat(None, mgr.list_names(), _cached_hardware()),
            }

        if run_manager.is_workspace_busy(workspace):
            return self._send_json(
                409,
                {
                    "error": "Já existe uma execução neste projeto. Cancele ou aguarde.",
                    "busy": True,
                },
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        run_id = run_manager.acquire(str(workspace))
        if not run_id:
            self._send_sse({"type": "error", "error": "Workspace ocupado por outra execução."})
            return

        model = models["coder"]
        self._send_sse({"type": "started", "run_id": run_id, "mode": "chat", "model": model})
        try:
            from local_agent.config import AgentConfig
            from local_agent.ollama_client import OllamaClient

            cfg = AgentConfig.from_args(workspace, model=model, no_memory=True, no_git=True)
            cfg.run_id = run_id
            cfg.cancel_check = lambda: run_manager.is_cancelled(run_id)
            client = OllamaClient(cfg)

            history = self._chat_history_for_ollama(workspace)
            history.append({"role": "user", "content": prompt})
            system = (
                "Você é o assistente sênior do Forge — especialista full-stack "
                "(frontend e backend) em várias linguagens: JavaScript/TypeScript/React, "
                "HTML/CSS, Python, Node, Go, Rust, Java e SQL. "
                "Responda em português, de forma clara e com boas práticas de engenharia. "
                "Este é o modo Chat: explique arquitetura, trade-offs e orientação — não edite arquivos. "
                "Se o usuário pedir para criar/editar código, diga que o Forge executa o pedido "
                "no projeto (modo Executar) aplicando padrão sênior. "
                f"Projeto atual: {workspace.name}."
            )

            def on_chunk(text: str) -> None:
                if run_manager.is_cancelled(run_id):
                    return
                self._send_sse({"type": "chat_chunk", "text": text})

            try:
                answer = client.stream_chat(
                    history,
                    model=model,
                    system=system,
                    temperature=0.4,
                    timeout=180,
                    on_chunk=on_chunk,
                    cancel_check=lambda: run_manager.is_cancelled(run_id),
                )
            except Exception as stream_exc:
                msg = str(stream_exc).lower()
                if "empty streaming" not in msg and "404" not in msg and "not found" not in msg:
                    raise
                # Retry once without relying on the failed stream path.
                self._send_sse({"type": "chat_chunk", "text": ""})
                answer = client.chat(
                    history,
                    model=model,
                    system=system,
                    temperature=0.4,
                    timeout=180,
                )
                if answer:
                    self._send_sse({"type": "chat_chunk", "text": answer})
            if run_manager.is_cancelled(run_id):
                self._send_sse({"type": "cancelled", "run_id": run_id})
                self._send_sse({"type": "done", "ok": False, "status": "CANCELLED", "mode": "chat", "run_id": run_id})
                return

            if project_id:
                append_message(workspace, "agent", answer, meta={"mode": "chat", "model": model, "run_id": run_id})
            self._send_sse(
                {
                    "type": "done",
                    "ok": True,
                    "status": "SUCCESS",
                    "mode": "chat",
                    "summary": answer,
                    "report": answer,
                    "model": model,
                    "run_id": run_id,
                    "created_files": [],
                    "modified_files": [],
                }
            )
        except Exception as exc:
            message = str(exc)
            if "cancelled" in message.lower():
                self._send_sse({"type": "cancelled", "run_id": run_id})
                self._send_sse({"type": "done", "ok": False, "status": "CANCELLED", "mode": "chat", "run_id": run_id})
            else:
                self._send_sse({"type": "error", "error": message})
                self._send_sse({"type": "done", "ok": False, "status": "FAILED", "mode": "chat", "error": message})
        finally:
            run_manager.clear(run_id)

    def _handle_run_stream(self) -> None:
        data = self._read_json()
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return self._send_json(400, {"error": "prompt is required"})

        try:
            workspace = _resolve_workspace(data.get("workspace") or data.get("project_path"))
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        workspace.mkdir(parents=True, exist_ok=True)
        project_id = _project_id_from_workspace(workspace)

        models, conversation, preflight_error = self._prepare_run(data, workspace)
        if preflight_error:
            return self._send_json(self._preflight_status(preflight_error), preflight_error)

        if run_manager.is_workspace_busy(workspace):
            return self._send_json(
                409,
                {
                    "error": "Agente já em execução neste projeto. Aguarde ou cancele a execução atual.",
                    "busy": True,
                },
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        run_id = run_manager.acquire(str(workspace))
        if not run_id:
            self._send_sse({"type": "error", "error": "Workspace ocupado por outra execução."})
            return

        self._send_sse({"type": "started", "run_id": run_id, "goal": prompt})
        try:
            from local_agent.agent import CodingAgent

            config = self._build_agent_config(data, workspace, models)
            config.run_id = run_id
            config.cancel_check = lambda: run_manager.is_cancelled(run_id)
            agent = CodingAgent(config, event_sink=self._send_sse)
            report = agent.run(prompt, conversation_context=conversation)
            result = self._finalize_run(workspace, project_id, report, run_id=run_id)
            self._send_sse({"type": "done", **result})
        except Exception as exc:
            self._send_sse({"type": "error", "error": str(exc), "trace": traceback.format_exc()[-1200:]})
        finally:
            run_manager.clear(run_id)

    def _handle_run(self) -> None:
        data = self._read_json()
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return self._send_json(400, {"error": "prompt is required"})

        try:
            workspace = _resolve_workspace(data.get("workspace") or data.get("project_path"))
        except ValueError as exc:
            return self._send_json(400, {"error": str(exc)})
        workspace.mkdir(parents=True, exist_ok=True)
        project_id = _project_id_from_workspace(workspace)

        models, conversation, preflight_error = self._prepare_run(data, workspace)
        if preflight_error:
            return self._send_json(self._preflight_status(preflight_error), preflight_error)

        if run_manager.is_workspace_busy(workspace):
            return self._send_json(
                409,
                {"error": "Agente já em execução neste projeto.", "busy": True},
            )

        run_id = run_manager.acquire(str(workspace))
        if not run_id:
            return self._send_json(409, {"error": "Workspace ocupado.", "busy": True})

        try:
            from local_agent.agent import CodingAgent

            config = self._build_agent_config(data, workspace, models)
            config.run_id = run_id
            report = CodingAgent(config).run(prompt, conversation_context=conversation)
            self._send_json(200, self._finalize_run(workspace, project_id, report, run_id=run_id))
        except Exception as exc:
            self._send_json(500, {"error": str(exc), "trace": traceback.format_exc()[-2000:]})
        finally:
            run_manager.clear(run_id)

    def _serve_file(self, file_path: Path) -> None:
        if not file_path.is_file():
            self._send_json(404, {"error": "file not found"})
            return
        content = file_path.read_bytes()
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        if ctype and (ctype.startswith("text/") or ctype in {"application/javascript", "text/css"}):
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Forge — local app generation platform")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)

    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((args.host, args.port), PlatformHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"Forge Platform v{PLATFORM_VERSION} running at {url}")
    print(f"Setup API: /api/setup/stream (auto-install Ollama + model)")
    print(f"Projects root: {PROJECTS_ROOT}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        dev_manager.stop_all()
        ollama_service.stop_if_started()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
