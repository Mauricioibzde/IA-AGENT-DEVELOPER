"""One-click deploy helpers (Vercel-first, local fallback instructions)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def _has_build_script(project_dir: Path) -> bool:
    package_json = project_dir / "package.json"
    if not package_json.is_file():
        return False
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return isinstance(scripts, dict) and "build" in scripts


def ensure_vercel_config(project_dir: Path) -> Path:
    vercel_path = project_dir / "vercel.json"
    if vercel_path.exists():
        return vercel_path

    if _has_build_script(project_dir):
        config = {
            "version": 2,
            "buildCommand": "npm run build",
            "outputDirectory": "dist",
        }
        package_json = project_dir / "package.json"
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
            deps = pkg.get("dependencies") or {}
            if "next" in deps:
                config = {"version": 2}
            elif "vite" in (pkg.get("devDependencies") or {}) or "vite" in deps:
                config["outputDirectory"] = "dist"
        except (json.JSONDecodeError, OSError):
            pass
    elif (project_dir / "index.html").is_file():
        config = {"version": 2, "cleanUrls": True}
    else:
        config = {"version": 2}

    vercel_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return vercel_path


def _extract_url(output: str) -> Optional[str]:
    for line in output.splitlines():
        match = re.search(r"https://[^\s]+\.vercel\.app", line)
        if match:
            return match.group(0)
    return None


def manual_deploy_steps(project_name: str) -> List[str]:
    return [
        "Instale Node.js e faça login: npm i -g vercel && vercel login",
        f"Entre na pasta: cd projects/{project_name}",
        "Deploy: vercel --yes",
        "Produção: vercel --prod",
        "Ou defina VERCEL_TOKEN no .env e use o botão Deploy na plataforma.",
    ]


def deploy_preflight(project_dir: Path) -> Dict[str, Any]:
    """Checklist for the deploy modal (does not expose the token value)."""
    token = bool(os.environ.get("VERCEL_TOKEN", "").strip())
    npm = shutil.which("npm") is not None
    npx = shutil.which("npx") is not None
    vercel_cli = shutil.which("vercel") is not None
    has_build = _has_build_script(project_dir)
    has_index = (project_dir / "index.html").is_file()
    requirements = [
        {"id": "token", "ok": token, "label": "VERCEL_TOKEN configurado", "fix": "Defina VERCEL_TOKEN no .env do servidor"},
        {"id": "node", "ok": npm or npx or vercel_cli, "label": "Node/npx/vercel disponível", "fix": "Instale Node.js: https://nodejs.org"},
        {"id": "app", "ok": has_build or has_index, "label": "App com build ou index.html", "fix": "Crie um site ou app no projeto"},
    ]
    return {
        "token_configured": token,
        "npm_available": npm,
        "npx_available": npx,
        "vercel_cli": vercel_cli,
        "has_build_script": has_build,
        "has_index_html": has_index,
        "ready": all(r["ok"] for r in requirements),
        "requirements": requirements,
    }


def deploy_project(project_dir: Path, project_name: str) -> Dict[str, Any]:
    ensure_vercel_config(project_dir)
    preflight = deploy_preflight(project_dir)
    token = os.environ.get("VERCEL_TOKEN", "").strip()
    npx = shutil.which("npx")
    vercel = shutil.which("vercel")

    if not token:
        return {
            "ok": False,
            "manual": True,
            "message": "VERCEL_TOKEN não configurado. Configure o token ou siga o deploy manual.",
            "steps": manual_deploy_steps(project_name),
            "vercel_config": str(project_dir / "vercel.json"),
            "requirements": preflight["requirements"],
        }

    if not npx and not vercel:
        return {
            "ok": False,
            "manual": True,
            "message": "CLI Vercel não encontrada. Instale Node.js (npx) ou a CLI vercel.",
            "steps": manual_deploy_steps(project_name),
            "requirements": preflight["requirements"],
        }

    cmd: List[str]
    if npx:
        cmd = ["npx", "--yes", "vercel", "deploy", "--yes", "--token", token]
    else:
        cmd = ["vercel", "deploy", "--yes", "--token", token]

    prod = os.environ.get("VERCEL_PROD", "").lower() in {"1", "true", "yes"}
    if prod:
        cmd.append("--prod")

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "manual": False,
            "message": "Deploy excedeu o tempo limite (10 min).",
            "steps": manual_deploy_steps(project_name),
            "requirements": preflight["requirements"],
        }

    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    url = _extract_url(output)
    if completed.returncode == 0 and url:
        return {
            "ok": True,
            "url": url,
            "message": "Deploy concluído com sucesso",
            "log_tail": output[-1500:],
            "requirements": preflight["requirements"],
        }

    return {
        "ok": False,
        "manual": False,
        "message": "Deploy via CLI falhou ou a URL não foi detectada. Veja o log e os requisitos.",
        "log_tail": output[-2000:],
        "steps": manual_deploy_steps(project_name),
        "requirements": preflight["requirements"],
    }
