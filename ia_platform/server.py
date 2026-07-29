"""Local web platform server (stdlib only — no FastAPI required)."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_WORKSPACE = ROOT.parent / "sandbox"


class PlatformHandler(BaseHTTPRequestHandler):
    server_version = "IAAgentPlatform/1.0"

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
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._handle_health()
        if path in {"/", "/index.html"}:
            return self._serve_file(STATIC / "index.html")
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            return self._serve_file(STATIC / rel)
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/run":
            return self._handle_run()
        self._send_json(404, {"error": "not found"})

    def _handle_health(self) -> None:
        from local_agent.config import AgentConfig
        from local_agent.ollama_client import OllamaClient

        cfg = AgentConfig.from_args(DEFAULT_WORKSPACE, no_memory=True)
        client = OllamaClient(cfg)
        ollama_ok = client.check_available()
        models = client.list_models() if ollama_ok else []
        self._send_json(
            200,
            {
                "ok": True,
                "agent": True,
                "ollama": ollama_ok,
                "models": models[:20],
                "workspace": str(DEFAULT_WORKSPACE),
            },
        )

    def _handle_run(self) -> None:
        data = self._read_json()
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return self._send_json(400, {"error": "prompt is required"})

        workspace = Path(str(data.get("workspace") or "sandbox"))
        if not workspace.is_absolute():
            workspace = (ROOT.parent / workspace).resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            from local_agent.agent import CodingAgent
            from local_agent.config import AgentConfig

            config = AgentConfig.from_args(
                workspace,
                model=data.get("model"),
                max_steps=int(data.get("max_steps") or 12),
                dry_run=bool(data.get("dry_run")),
                plan_only=bool(data.get("plan_only")),
                verbose=True,
            )
            report = CodingAgent(config).run(prompt)
            self._send_json(
                200,
                {
                    "ok": True,
                    "status": report.status.value,
                    "report": report.render(),
                    "workspace": str(workspace),
                },
            )
        except Exception as exc:
            self._send_json(
                500,
                {
                    "error": str(exc),
                    "trace": traceback.format_exc()[-2000:],
                },
            )

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
    parser = argparse.ArgumentParser(description="IA Agent Developer local platform")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)

    DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((args.host, args.port), PlatformHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"IA Agent Platform running at {url}")
    print(f"Workspace default: {DEFAULT_WORKSPACE}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
