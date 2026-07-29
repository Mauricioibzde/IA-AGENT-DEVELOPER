# IA Agent Developer v1.0 — MVP Local

Agente local de programação com Ollama + interface web para criar sites/apps por conversa.

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

---

## Modos de uso

| Modo | Comando | Para quê |
|------|---------|----------|
| **Web UI** | `scripts/run-platform.ps1` | Chat estilo plataforma (local) |
| **CLI** | `python -m local_agent "..." --workspace sandbox` | Terminal / automação |
| **VS Code** | `Ctrl+Shift+P` → Tasks → *IA Agent* | Atalhos no editor |
| **Legado** | `python ollama_agent.py "..."` | Compatibilidade |

---

## Exemplos de prompt (web ou CLI)

```
Crie uma landing page HTML/CSS moderna para uma startup de IA
```

```
Crie uma API FastAPI com endpoint /health e testes pytest
```

```
Crie um app React simples com navbar e hero section na pasta sandbox/site
```

```
Analise o projeto e corrija erros de sintaxe Python
```

---

## Arquitetura

```text
local_agent/          # motor do agente (planner, tools, validator, reflector)
ia_ia_platform/             # UI web local + API /api/run
scripts/              # setup, run-platform, start-today
sandbox/              # projetos gerados pelo agente
```

---

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.com/)
- Modelo recomendado: `qwen2.5-coder:7b` (leve) ou `qwen3-coder:30b` (melhor, precisa GPU)

```powershell
ollama pull qwen2.5-coder:7b
```

---

## Testes

```bash
python -m pytest -q
```

46+ testes unitários (sem depender de Ollama para a maioria).

---

## VS Code Tasks

- **IA Agent: Start Platform (Web UI)** — abre servidor local
- **IA Agent: CLI Execute** — roda prompt no terminal
- **IA Agent: Plan Only** — só gera plano
- **IA Agent: Run Tests** — pytest

---

## Segurança

- Paths confinados ao workspace
- Comandos perigosos bloqueados
- `--dry-run` para simular sem escrever disco
- Backups `.bak` em edições

---

## Roadmap pós-MVP

- [ ] Embeddings/RAG para projetos grandes
- [ ] Preview automático (npm run dev)
- [ ] Deploy 1-clique (Vercel)
- [ ] Multi-usuário + cloud beta

---

## Licença

MIT
