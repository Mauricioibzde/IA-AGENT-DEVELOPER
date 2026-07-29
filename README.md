# IA Agent Developer v1.0 — MVP Local (Forge)

Agente local de programação com Ollama + interface web **Forge** para criar sites/apps por conversa (fluxo estilo Lovable).

## Terminar o projeto hoje (3 passos)

### Windows

```powershell
# Terminal 1
ollama serve

# Terminal 2 — setup + testes + plataforma web
powershell -ExecutionPolicy Bypass -File .\scripts\start-today.ps1
```

Abra no navegador: **http://127.0.0.1:8787**

### Linux/macOS

```bash
ollama serve   # terminal 1
bash scripts/setup.sh
python3 -m pytest -q
bash scripts/run-platform.sh
```

Requisitos extras para preview React: **Node.js + npm**.

---

## Modos de uso

| Modo | Comando | Para quê |
|------|---------|----------|
| **Web UI (Forge)** | `scripts/run-platform.ps1` / `run-platform.sh` | Chat + Executar + Preview ao vivo |
| **CLI** | `python -m local_agent "..." --workspace sandbox` | Terminal / automação |
| **VS Code** | `Ctrl+Shift+P` → Tasks → *IA Agent* | Atalhos no editor |
| **Legado** | `python ollama_agent.py "..."` | Compatibilidade |

Na UI, o modo **Chat** responde rápido; pedidos claros de desenvolvimento (criar/editar app, landing, API…) são roteados automaticamente para **Executar código**.

---

## Exemplos de prompt (web ou CLI)

```
Crie uma landing page HTML/CSS moderna para uma startup de IA
```

```
Crie uma API FastAPI com endpoint /health e testes pytest
```

```
Crie um app React simples com navbar e hero section
```

```
Analise o projeto e corrija erros de sintaxe Python
```

---

## Arquitetura

```text
local_agent/          # motor do agente (planner, tools, validator, reflector)
ia_platform/          # UI web Forge + API /api/run + preview/dev
scripts/              # setup, run-platform, start-today
projects/             # projetos criados pela UI (sandbox seguro)
sandbox/              # workspace CLI / legado
```

Workspaces da API ficam restritos a `projects/` e `sandbox/`.

---

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.com/)
- Modelo recomendado: `qwen2.5-coder:7b` (leve) ou `qwen3-coder:30b` (melhor, precisa GPU)
- Node.js (opcional, para `npm run dev` / preview React)

```powershell
ollama pull qwen2.5-coder:7b
```

---

## Testes

```bash
python -m pytest -q
```

100+ testes unitários (sem depender de Ollama para a maioria).

---

## VS Code Tasks

- **IA Agent: Start Platform (Web UI)** — abre servidor local
- **IA Agent: CLI Execute** — roda prompt no terminal
- **IA Agent: Plan Only** — só gera plano
- **IA Agent: Run Tests** — pytest

---

## Segurança

- Paths confinados ao workspace (`projects/` / `sandbox/` na plataforma)
- Comandos perigosos bloqueados
- `--dry-run` para simular sem escrever disco
- Backups `.bak` em edições

---

## Roadmap pós-MVP

- [ ] Embeddings/RAG para projetos grandes
- [x] Preview automático (npm run dev)
- [x] Deploy 1-clique (Vercel)
- [x] Chat rápido + auto-execução de pedidos de build
- [ ] Multi-usuário + cloud beta

---

## Licença

MIT
