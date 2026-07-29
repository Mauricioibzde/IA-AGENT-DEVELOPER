"""Deterministic plain HTML/CSS/JS starters for when the LLM is unavailable."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


def looks_like_plain_web_goal(goal: str) -> bool:
    """True for small static HTML/CSS/JS apps (not React/Vite/API)."""
    g = (goal or "").lower()
    if re.search(r"\b(react|vite|next\.?js|fastapi|flask|express|django|api rest|backend)\b", g):
        return False
    has_web = bool(
        re.search(
            r"\b(html|css|javascript|\bjs\b|site|página|pagina|landing|aplicat|app|se[cç][aã]o|section|layout)\b",
            g,
        )
    )
    wants_create = bool(
        re.search(
            r"\b(cri(e|ar)|faz(er)?|mont(e|ar)|gera(r)?|build|pequena|simples|mini|melhor(e|ar)|adicion|alter|edit|atualiz|implement|inclu)\b",
            g,
        )
    )
    has_stack = bool(re.search(r"\bhtml\b", g) and re.search(r"\b(css|javascript|\bjs\b)\b", g))
    # Follow-ups like "implemente as melhorias" after a static app conversation.
    implement_followup = bool(
        re.search(r"\b(implement(e|ar)?|aplique|aplica|melhorias?|sugest\w*)\b", g)
    )
    return (has_web and (wants_create or has_stack)) or (implement_followup and has_web)


def is_plain_web_workspace(workspace: Path) -> bool:
    """Detect an existing static HTML/CSS/JS project (no package.json / Python app)."""
    root = Path(workspace)
    if not root.is_dir():
        return False
    if (root / "package.json").exists() or (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return False
    names = {p.name.lower() for p in root.iterdir() if p.is_file()}
    has_html = "index.html" in names or any(n.endswith(".html") for n in names)
    has_asset = any(n.endswith((".css", ".js")) for n in names)
    has_py = any(n.endswith(".py") for n in names)
    return has_html and has_asset and not has_py


def looks_like_react_goal(goal: str) -> bool:
    g = (goal or "").lower()
    if re.search(r"\b(fastapi|flask|django|api rest)\b", g) and not re.search(r"\b(react|vite)\b", g):
        return False
    return bool(re.search(r"\b(react|vite|next\.?js|spa)\b", g)) and bool(
        re.search(r"\b(cri(e|ar)|faz(er)?|mont(e|ar)|gera(r)?|app|aplicat|site|dashboard|landing)\b", g)
    )


def looks_like_fastapi_goal(goal: str) -> bool:
    g = (goal or "").lower()
    if re.search(r"\b(react|vite|html|css)\b", g) and not re.search(r"\b(fastapi|api|endpoint|backend)\b", g):
        return False
    has_api = bool(re.search(r"\b(fastapi|api rest|endpoint|/health|backend python)\b", g))
    wants = bool(re.search(r"\b(cri(e|ar)|faz(er)?|mont(e|ar)|gera(r)?|implement)\b", g))
    return has_api and wants


def looks_like_offline_scaffold_goal(goal: str) -> bool:
    return looks_like_plain_web_goal(goal) or looks_like_react_goal(goal) or looks_like_fastapi_goal(goal)


def _title_from_goal(goal: str) -> str:
    g = (goal or "").strip()
    # Prefer a short friendly default for tiny demos.
    if len(g) > 60:
        return "Minha App"
    cleaned = re.sub(r"\s+", " ", g)
    if looks_like_plain_web_goal(g) and len(cleaned) > 40:
        return "Minha App"
    return "Minha App"


def plain_web_files(title: str = "Minha App") -> Dict[str, str]:
    """Minimal polished single-page app: index.html + style.css + app.js."""
    return {
        "index.html": f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <main class="app">
    <p class="brand">Forge</p>
    <h1>{title}</h1>
    <p class="lede">Uma app pequena em HTML, CSS e JavaScript — pronta para evoluir no chat.</p>
    <div class="card">
      <p class="label">Contador</p>
      <p class="value" id="count">0</p>
      <div class="actions">
        <button type="button" id="btnMinus" aria-label="Diminuir">−</button>
        <button type="button" id="btnPlus" class="primary" aria-label="Aumentar">+</button>
        <button type="button" id="btnReset">Zerar</button>
      </div>
    </div>
  </main>
  <script src="app.js"></script>
</body>
</html>
""",
        "style.css": """* { box-sizing: border-box; margin: 0; }
:root {
  --bg: #0b1220;
  --surface: #121a2b;
  --text: #f8fafc;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --line: rgba(148, 163, 184, 0.22);
}
body {
  min-height: 100vh;
  font-family: "Segoe UI", system-ui, sans-serif;
  color: var(--text);
  background:
    radial-gradient(ellipse 70% 45% at 50% -10%, rgba(56, 189, 248, 0.22), transparent),
    linear-gradient(180deg, #0b1220, #111827);
}
.app {
  max-width: 28rem;
  margin: 0 auto;
  padding: 3.5rem 1.25rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.85rem;
}
.brand {
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 0.72rem;
  color: var(--accent);
  font-weight: 600;
}
h1 {
  font-size: clamp(1.8rem, 5vw, 2.4rem);
  letter-spacing: -0.03em;
  line-height: 1.15;
}
.lede {
  color: var(--muted);
  line-height: 1.55;
  max-width: 26rem;
}
.card {
  margin-top: 1rem;
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 1.35rem 1.2rem 1.2rem;
}
.label {
  color: var(--muted);
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}
.value {
  font-size: 2.75rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  margin-bottom: 1rem;
}
.actions {
  display: flex;
  gap: 0.55rem;
  justify-content: center;
  flex-wrap: wrap;
}
button {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--text);
  border-radius: 999px;
  padding: 0.65rem 1.1rem;
  font-size: 1rem;
  cursor: pointer;
}
button.primary {
  background: var(--text);
  color: #0f172a;
  border-color: transparent;
  font-weight: 650;
}
button:hover { filter: brightness(1.08); }
button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
""",
        "app.js": """(() => {
  const countEl = document.getElementById("count");
  const btnPlus = document.getElementById("btnPlus");
  const btnMinus = document.getElementById("btnMinus");
  const btnReset = document.getElementById("btnReset");
  let count = 0;

  function render() {
    countEl.textContent = String(count);
  }

  btnPlus.addEventListener("click", () => {
    count += 1;
    render();
  });
  btnMinus.addEventListener("click", () => {
    count -= 1;
    render();
  });
  btnReset.addEventListener("click", () => {
    count = 0;
    render();
  });

  render();
})();
""",
        "README.md": f"""# {title}

App pequena em HTML, CSS e JavaScript.

Abra `index.html` no preview da plataforma ou em um navegador.

Peça no chat: melhorias visuais, novas seções ou lógica extra.
""",
    }


def write_plain_web_app(workspace: Path, goal: str = "") -> Tuple[List[str], str]:
    """Write the starter files into workspace. Returns (created_paths, title)."""
    title = _title_from_goal(goal)
    files = plain_web_files(title)
    created: List[str] = []
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(rel.replace("\\", "/"))
    return created, title


def fastapi_files(project_name: str = "forge-api") -> Dict[str, str]:
    name = re.sub(r"[^a-zA-Z0-9_-]", "-", (project_name or "forge-api").strip().lower())[:64] or "forge-api"
    return {
        "main.py": '''"""API FastAPI gerada pelo Forge."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Forge API", version="0.1.0")


class Health(BaseModel):
    ok: bool
    service: str = "forge-api"


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(ok=True)


@app.get("/")
def root() -> dict:
    return {"message": "API pronta — peça novos endpoints no chat."}
''',
        "requirements.txt": "fastapi>=0.115.0\nuvicorn[standard]>=0.32.0\npytest>=8.0\nhttpx>=0.27.0\n",
        "tests/test_health.py": '''from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
''',
        "README.md": f"""# {name}

API FastAPI gerada pelo Forge.

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Health: http://127.0.0.1:8000/health

Testes: `pytest -q`
""",
    }


def write_react_app(workspace: Path, goal: str = "") -> Tuple[List[str], str]:
    from ia_platform.project_templates import react_vite_files

    title = "Forge React App"
    g = (goal or "").strip()
    if 3 < len(g) <= 40:
        title = g
    files = react_vite_files(title)
    created: List[str] = []
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(rel.replace("\\", "/"))
    return created, title


def write_fastapi_app(workspace: Path, goal: str = "") -> Tuple[List[str], str]:
    title = "forge-api"
    files = fastapi_files(title)
    created: List[str] = []
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(rel.replace("\\", "/"))
    return created, title


def validate_plain_web(workspace: Path) -> List[str]:
    """Return list of problems for a static HTML/CSS/JS app (empty = ok)."""
    problems: List[str] = []
    root = Path(workspace)
    index = root / "index.html"
    if not index.is_file():
        problems.append("index.html ausente")
        return problems
    html = index.read_text(encoding="utf-8", errors="ignore")
    if 'href="style.css"' in html or "href='style.css'" in html:
        if not (root / "style.css").is_file():
            problems.append("style.css referenciado mas ausente")
    if 'src="app.js"' in html or "src='app.js'" in html:
        if not (root / "app.js").is_file():
            problems.append("app.js referenciado mas ausente")
    for name in ("style.css", "app.js"):
        path = root / name
        if path.is_file() and path.stat().st_size == 0:
            problems.append(f"{name} está vazio")
    return problems
