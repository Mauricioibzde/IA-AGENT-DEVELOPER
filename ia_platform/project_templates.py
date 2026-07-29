"""Shared project starter templates (UI create + agent scaffold)."""

from __future__ import annotations

import json
import re
from typing import Dict


def _pkg_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", (name or "app").strip().lower())[:64]
    return cleaned or "app"


def react_vite_files(project_name: str = "forge-react-app") -> Dict[str, str]:
    """Full Vite + React starter that works with the platform dev preview."""
    name = _pkg_name(project_name)
    return {
        "package.json": json.dumps(
            {
                "name": name,
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
  server: { host: "127.0.0.1", port: Number(process.env.PORT) || 5173 },
});
""",
        "index.html": f"""<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
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
        "src/App.jsx": """import "./App.css";

export default function App() {
  return (
    <main className="app">
      <p className="eyebrow">Forge</p>
      <h1>Seu app começa aqui</h1>
      <p className="lede">Descreva no chat o que quer construir — o preview atualiza ao vivo.</p>
      <button type="button" onClick={() => alert("Pronto para iterar")}>
        Começar
      </button>
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
  gap: 0.85rem;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(56, 189, 248, 0.22), transparent),
    linear-gradient(165deg, #0c1222 0%, #111827 45%, #0f172a 100%);
  color: #f8fafc;
  font-family: "Segoe UI", system-ui, sans-serif;
  text-align: center;
  padding: 2rem;
}

.eyebrow {
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 0.72rem;
  color: #7dd3fc;
  font-weight: 600;
}

h1 {
  font-size: clamp(1.85rem, 4vw, 2.75rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  max-width: 16ch;
  line-height: 1.15;
}

.lede {
  color: #94a3b8;
  max-width: 34rem;
  line-height: 1.55;
}

button {
  margin-top: 0.5rem;
  border: none;
  border-radius: 999px;
  padding: 0.8rem 1.4rem;
  background: #f8fafc;
  color: #0f172a;
  font-weight: 650;
  cursor: pointer;
}

button:hover {
  background: #e2e8f0;
}
""",
        "src/index.css": """* { box-sizing: border-box; margin: 0; }
body { min-height: 100vh; }
""",
        "README.md": f"""# {project_name}

App React + Vite gerado pelo Forge.

```bash
npm install
npm run dev
```
""",
    }


PROJECT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "blank": {},
    "landing": {
        "index.html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Landing</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="hero">
    <p class="brand">Forge</p>
    <h1>Seu produto, no ar hoje</h1>
    <p class="sub">Descreva no chat o que quer mudar — a preview atualiza na hora.</p>
    <a class="cta" href="#features">Começar agora</a>
  </header>
  <section id="features" class="features">
    <article>
      <h2>Rápido</h2>
      <p>Itere em linguagem natural e veja o resultado no preview.</p>
    </article>
    <article>
      <h2>Visual</h2>
      <p>Layout limpo, tipografia forte, pronto para personalizar.</p>
    </article>
    <article>
      <h2>Local</h2>
      <p>Roda na sua máquina com Ollama — sem depender da nuvem.</p>
    </article>
  </section>
</body>
</html>
""",
        "style.css": """* { box-sizing: border-box; margin: 0; }
body {
  font-family: "Segoe UI", system-ui, sans-serif;
  background: #0b1220;
  color: #f8fafc;
}
.hero {
  min-height: 88vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2.5rem 1.5rem;
  gap: 1rem;
  background:
    radial-gradient(ellipse 70% 45% at 50% 0%, rgba(56, 189, 248, 0.2), transparent),
    linear-gradient(180deg, #0b1220, #111827);
}
.brand {
  letter-spacing: 0.2em;
  text-transform: uppercase;
  font-size: 0.75rem;
  color: #7dd3fc;
  font-weight: 600;
}
.hero h1 {
  font-size: clamp(2.2rem, 6vw, 3.6rem);
  letter-spacing: -0.03em;
  max-width: 14ch;
  line-height: 1.1;
}
.sub { color: #94a3b8; max-width: 28rem; line-height: 1.55; }
.cta {
  display: inline-block;
  margin-top: 0.75rem;
  padding: 0.85rem 1.5rem;
  background: #f8fafc;
  color: #0f172a;
  text-decoration: none;
  border-radius: 999px;
  font-weight: 650;
}
.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  padding: 2.5rem 1.5rem 3.5rem;
  max-width: 960px;
  margin: 0 auto;
}
.features article {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(148,163,184,0.18);
  border-radius: 16px;
  padding: 1.25rem;
}
.features h2 { font-size: 1.05rem; margin-bottom: 0.4rem; }
.features p { color: #94a3b8; font-size: 0.92rem; line-height: 1.5; }
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
    <aside class="nav">
      <p class="brand">Forge</p>
      <h2>Painel</h2>
    </aside>
    <main>
      <h1>Dashboard</h1>
      <p class="sub">Peça no chat novos cards, filtros ou gráficos.</p>
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
body { font-family: "Segoe UI", system-ui, sans-serif; background: #0b1220; color: #fafafa; }
.layout { display: grid; grid-template-columns: 220px 1fr; min-height: 100vh; }
.nav { background: #070b14; padding: 1.5rem; border-right: 1px solid #1f2937; }
.brand { letter-spacing: 0.16em; text-transform: uppercase; font-size: 0.7rem; color: #7dd3fc; margin-bottom: 1rem; }
main { padding: 2rem; }
.sub { color: #94a3b8; margin-top: 0.35rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
.card {
  background: linear-gradient(160deg, #111827, #0f172a);
  border: 1px solid #1f2937;
  padding: 1.25rem;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.card span { color: #94a3b8; font-size: 0.85rem; }
.card strong { font-size: 1.5rem; }
""",
        "app.js": "console.log('Dashboard pronto — peça melhorias no chat da plataforma.');\n",
    },
    "react": {},  # filled below with react_vite_files()
}

PROJECT_TEMPLATES["react"] = react_vite_files("forge-react-app")
