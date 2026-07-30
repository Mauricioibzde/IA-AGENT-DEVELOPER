# IA Agent Developer v1.0 — MVP Local (Forge)

Agente local de programação com Ollama + interface web **Forge** para criar sites/apps por conversa (fluxo estilo Lovable).

## Importante: local vs túnel remoto

Se o modal **Modelos IA** mostrar algo como:

> navegador em Windows, Forge/Ollama em Linux (`cursor`) / container

você está abrindo o Forge **remoto** (túnel do agente/cloud). Nesse caso:

- o hardware e o download de modelos são da **VM Linux**, não do seu PC
- a GPU/RAM do Windows **não** entram nas recomendações

Para usar **este computador Windows**:

1. Clone/abra o repositório **no seu PC**
2. Suba o Forge localmente (comandos abaixo)
3. Abra `http://127.0.0.1:8787` e confirme em Modelos IA: **SO = Windows** e host **diferente de `cursor`**

---

## Terminar o projeto hoje (3 passos)

### Windows (recomendado no seu PC)

```powershell
# Terminal 1 — Ollama (ícone da llama ou:)
ollama serve

# Terminal 2 — na pasta do repositório
powershell -ExecutionPolicy Bypass -File .\scripts\start-today.ps1
```

Ou só a UI, se o setup já foi feito:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-platform.ps1
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
ia_platform/visual_engine/  # fachada Python do Visual Engine
visual_engine/        # núcleo Node (Puppeteer + pixelmatch) — sem servidor próprio
docs/                 # VISUAL_ENGINE.md + migração do puppeteer-compare
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

## Visual Engine (em migração)

Comparação visual integrada a partir do [puppeteer-compare](https://github.com/Mauricioibzde/puppeteer-compare) — ver `docs/MIGRATION_FROM_PUPPETEER_COMPARE.md`.

```bash
cd visual_engine && npm install && npm test
python3 -m pytest ia_platform/test_visual_engine.py -q
```

Requisito: Node.js 18+ e Chrome/Chromium (no Windows os paths comuns são detectados automaticamente).

## Roadmap pós-MVP

- [ ] Embeddings/RAG para projetos grandes
- [x] Preview automático (npm run dev)
- [x] Deploy 1-clique (Vercel)
- [x] Chat rápido + auto-execução de pedidos de build
- [ ] Visual Engine completo (capture → compare → correction loop)
- [ ] Multi-usuário + cloud beta

---

## Licença

MIT
