"""Local web platform server for app generation."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from ia_platform.conversations import append_message, clear_messages, load_messages
from ia_platform.deploy import deploy_project
from ia_platform.dev_server import dev_manager
from ia_platform.hardware import detect_hardware
from ia_platform.model_catalog import recommend_models
from ia_platform.ollama_models import OllamaModelManager

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

STATIC = ROOT / "static"
PROJECTS_ROOT = ROOT.parent / "projects"
DEFAULT_WORKSPACE = ROOT.parent / "sandbox"
IGNORE_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".agent", ".pytest_cache"}

PROJECT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "blank": {},
    "landing": {
        "index.html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Landing Page</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="hero">
    <h1>Seu produto, lançado hoje</h1>
    <p>Descreva no chat o que quer mudar nesta landing page.</p>
    <a class="cta" href="#">Começar agora</a>
  </header>
</body>
</html>
""",
        "style.css": """* { box-sizing: border-box; margin: 0; }
body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; }
.hero { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 2rem; gap: 1rem; }
.hero h1 { font-size: clamp(2rem, 5vw, 3.5rem); }
.hero p { color: #94a3b8; max-width: 32rem; }
.cta { display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #6366f1; color: #fff; text-decoration: none; border-radius: 999px; font-weight: 600; }
""",
    },
    "api": {
        "main.py": '''"""API REST simples — peça ao agente para expandir endpoints."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
''',
        "README.md": "# API\n\nRode: `python main.py`\n\nPeça ao agente novos endpoints via chat.\n",
    },
    "dashboard": {
        "index.html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dashboard</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="layout">
    <aside class="nav"><h2>Painel</h2></aside>
    <main>
      <h1>Dashboard</h1>
      <div class="cards">
        <div class="card"><span>Usuários</span><strong>1.2k</strong></div>
        <div class="card"><span>Receita</span><strong>R$ 8.4k</strong></div>
        <div class="card"><span>Conversão</span><strong>3.2%</strong></div>
      </div>
    </main>
  </div>
  <script src="app.js"></script>
</body>
</html>
""",
        "style.css": """* { box-sizing: border-box; margin: 0; }
body { font-family: system-ui, sans-serif; background: #18181b; color: #fafafa; }
.layout { display: grid; grid-template-columns: 220px 1fr; min-height: 100vh; }
.nav { background: #09090b; padding: 1.5rem; border-right: 1px solid #27272a; }
main { padding: 2rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
.card { background: #27272a; padding: 1.25rem; border-radius: 12px; display: flex; flex-direction: column; gap: 0.5rem; }
.card span { color: #a1a1aa; font-size: 0.85rem; }
.card strong { font-size: 1.5rem; }
""",
        "app.js": "console.log('Dashboard pronto — peça melhorias no chat da plataforma.');\n",
    },
    "react": {
        "package.json": json.dumps(
            {
                "name": "forge-react-app",
                "private": True,
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
                "devDependencies": {"@vitejs/plugin-react": "^4.3.4", "vite": "^5.4.11"},
            },
            indent=2,
        )
        + "\n",
        "vite.config.js": """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173 },
});
""",
        "index.html": """<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Forge React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""",
        "src/main.jsx": """import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",
        "src/App.jsx": """export default function App() {
  return (
    <main className="app">
      <h1>React + Vite</h1>
      <p>Peça ao agente no chat para personalizar este app.</p>
      <button type="button" onClick={() => alert("Forge AI")}>Testar</button>
    </main>
  );
}
""",
        "src/App.css": """.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  background: radial-gradient(circle at top, #312e81, #0f172a 55%);
  color: #f8fafc;
  font-family: system-ui, sans-serif;
  text-align: center;
  padding: 2rem;
}

button {
  border: none;
  border-radius: 999px;
  padding: 0.75rem 1.25rem;
  background: #6366f1;
  color: white;
  font-weight: 600;
  cursor: pointer;
}
""",
        "src/index.css": "* { box-sizing: border-box; margin: 0; }\n",
    },
}


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
    if raw and raw.startswith("projects/"):
        return _project_path(raw.split("/", 1)[1])
    path = Path(raw or "sandbox")
    if not path.is_absolute():
        path = (ROOT.parent / path).resolve()
    return path


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
    files = PROJECT_TEMPLATES.get(template) or {}
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
        if path == "/api/projects":
            return self._handle_create_project()
        if path == "/api/models/pull/stream":
            return self._handle_model_pull_stream()
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

    def _handle_health(self) -> None:
        from local_agent.config import AgentConfig
        from local_agent.ollama_client import OllamaClient

        cfg = AgentConfig.from_args(PROJECTS_ROOT, no_memory=True)
        client = OllamaClient(cfg)
        ollama_ok = client.check_available()
        models = client.list_models() if ollama_ok else []
        recommendation = None
        if ollama_ok:
            hw = detect_hardware()
            recommendation = recommend_models(hw, models).get("primary")
        self._send_json(
            200,
            {
                "ok": True,
                "agent": True,
                "ollama": ollama_ok,
                "models": models[:20],
                "recommended_model": recommendation.get("ollama_name") if recommendation else None,
                "projects_root": str(PROJECTS_ROOT),
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
        if template == "blank" or template not in PROJECT_TEMPLATES:
            (project_dir / "README.md").write_text(readme, encoding="utf-8")
        else:
            _apply_template(project_dir, template)
            readme_path = project_dir / "README.md"
            if not readme_path.exists():
                readme_path.write_text(readme, encoding="utf-8")
        self._send_json(201, {"id": name, "name": name, "path": f"projects/{name}", "template": template})

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

    def _build_agent_config(self, data: Dict[str, Any], workspace: Path):
        from local_agent.config import AgentConfig

        return AgentConfig.from_args(
            workspace,
            model=data.get("model"),
            max_steps=int(data.get("max_steps") or 12),
            dry_run=bool(data.get("dry_run")),
            plan_only=bool(data.get("plan_only")),
            verbose=True,
        )

    def _finalize_run(self, workspace: Path, project_id: Optional[str], report) -> Dict[str, Any]:
        rendered = report.render()
        if project_id:
            append_message(
                workspace,
                "agent",
                rendered,
                meta={
                    "status": report.status.value,
                    "created_files": report.created_files,
                    "modified_files": report.modified_files,
                },
            )
        return {
            "ok": True,
            "status": report.status.value,
            "report": rendered,
            "workspace": str(workspace),
            "created_files": report.created_files,
            "modified_files": report.modified_files,
        }

    def _send_sse(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.wfile.write(b"data: " + body + b"\n\n")
        self.wfile.flush()

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

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            from local_agent.agent import CodingAgent

            config = self._build_agent_config(data, workspace)
            agent = CodingAgent(config, event_sink=self._send_sse)
            report = agent.run(prompt)
            result = self._finalize_run(workspace, project_id, report)
            self._send_sse({"type": "done", **result})
        except Exception as exc:
            self._send_sse({"type": "error", "error": str(exc), "trace": traceback.format_exc()[-1200:]})

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

        try:
            from local_agent.agent import CodingAgent

            config = self._build_agent_config(data, workspace)
            report = CodingAgent(config).run(prompt)
            self._send_json(200, self._finalize_run(workspace, project_id, report))
        except Exception as exc:
            self._send_json(500, {"error": str(exc), "trace": traceback.format_exc()[-2000:]})

    def _serve_file(self, file_path: Path) -> None:
        if not file_path.is_file():
            self._send_json(404, {"error": "file not found"})
            return
        content = file_path.read_bytes()
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
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
    print(f"Forge Platform running at {url}")
    print(f"Projects root: {PROJECTS_ROOT}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        dev_manager.stop_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
