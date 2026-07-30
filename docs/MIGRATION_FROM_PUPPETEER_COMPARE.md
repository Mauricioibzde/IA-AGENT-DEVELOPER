# Migração: Puppeteer Compare → Visual Engine (Forge)

**Status:** Fase 0–3 concluídas · Fase 4 (DOM/layout) a seguir  

**Branch:** `feature/visual-engine-integration`  
**Fonte:** https://github.com/Mauricioibzde/puppeteer-compare (branch `master`)  
**Destino:** `Mauricioibzde/IA-AGENT-DEVELOPER` (Forge / IA local)

---

## 1. Entendimento do objetivo

Integrar as capacidades úteis do **Puppeteer Compare** (Node/Express) no **Forge** (Python + Ollama) como um módulo interno **Visual Engine**, sem manter dois servidores, dois históricos ou duas UIs concorrentes.

O ciclo de produto desejado:

```text
pedido → plano → código → executar → capturar → comparar → diagnosticar → corrigir → (loop) → aprovar/rollback
```

---

## 2. Arquitetura atual — projeto principal (Forge)

| Camada | Path | Papel |
|--------|------|--------|
| Agente | `local_agent/` | Planner, tools, Ollama, validator, reflector, checkpoint |
| Plataforma | `ia_platform/` | HTTP (`server.py`), UI estática, preview, deploy, modelos |
| Preview ao vivo | `ia_platform/dev_server.py` | `npm`/`uvicorn` em `127.0.0.1:9200–9299` |
| Checkpoint | `local_agent/checkpoint.py` | Snapshots pré-mutação + undo |
| Histórico | `ia_platform/run_history.py` | Últimas runs em `.agent/runs.json` |
| Segurança | `local_agent/security.py` + allowlist de terminal | Workspace confinement |
| UI | `ia_platform/static/` | Chat/Work, Ao vivo, Arquivos, Preview, Relatório |

**Stack:** Python ≥3.11, stdlib HTTP, Ollama. **Sem** Chromium/Puppeteer/Playwright/pixelmatch hoje.  
**Deps de plataforma:** `pyproject.toml` sem runtime deps (pytest opcional).

---

## 3. Arquitetura atual — Puppeteer Compare

| Camada | Path | Papel |
|--------|------|--------|
| Server | `src/server.js` | Express + static UI + métricas |
| Orquestração | `src/services/compare.js` | URL×URL multi-viewport |
| Browser | `src/services/browser.js` | `puppeteer-core` + detecção Chrome (Win/Mac/Linux) |
| Capture | `src/services/screenshot.js` | goto + wait + PNG + HTML |
| Image | `src/services/image.js` | pngjs + pixelmatch (crop ao menor tamanho) |
| DOM | `src/services/domDiff/*` | jsdom + diff-dom |
| Artefatos | `artifacts/` + `cleanup.js` | Pastas por timestamp + retenção |
| Histórico | `services/database.js` | SQLite-like / JSON em `data/` |
| Presets | `config/config.js` → `DEVICE_PRESETS` | desktop/laptop/tablet/mobile |
| Segurança URL | `middleware/validator.js` | Bloqueia localhost/privados (SSRF) |
| Frontend | `public/` | UI própria (glassmorphism) — **não migrar** |

**Stack:** Node ≥18, ESM, Express, puppeteer-core, pixelmatch, pngjs, jsdom, diff-dom, winston.

---

## 4. Inventário A–E

### A. Reutilizar sem alterações importantes

- Presets de dispositivos (`DEVICE_PRESETS`)
- Detecção de Chrome no Windows (`browser.js` paths)
- `ensureDir` / `writePng` / `generateTimestampId`
- Thresholds conceituais (`THRESHOLDS.visual`)
- Ideia de cleanup por idade/contagem
- Ignore rules de seletores DOM (conceito)

### B. Reutilizar com refatoração

- `compare.js` orquestração → API unificada `compare({source,target,…})`
- `screenshot.js` → captura determinística (+ CSS de estabilização)
- `image.js` → normalização explícita (não só crop silencioso)
- `domDiff/*` → relatório estruturado (DOM / style / layout separados)
- `cleanup.js` → paths sob `projects/<id>/.agent/visual/`
- Validação de URL → **inverter** regra de localhost (permitir só projetos Forge)
- Logs Winston → eventos SSE do Forge (`run_manager`)

### C. Reescrever

- Servidor Express + rotas → handlers em `ia_platform/server.py`
- Frontend `public/` → abas Preview/Comparação do Forge
- Relatório HTML `report.js` → JSON para a IA + UI Forge
- Database isolada → histórico alinhado a `run_history` / artefatos do projeto
- Parallel viewports na **mesma** Page (bug de concorrência) → pages por viewport ou fila
- Score / regiões / overlay / slider (ausentes ou fracos)

### D. Não utilizar

- UI completa do Puppeteer Compare (`public/css/*` dezenas de folhas)
- Docker/Express como app separado
- Webhooks genéricos (fase futura se necessário)
- Rate limiter Express (substituir por limites no Forge)
- Scripts PowerShell de tradução de commits
- Showcase de ícones / date picker / tips UX do app antigo
- Bloqueio absoluto de localhost (incompatível com preview local)

### E. Ausente — criar no Forge

- Mockup × URL / imagem × imagem unificados
- Correlação pixel↔DOM com confiança
- Layout/style diff além de DOM
- Correction loop + Pixel Perfect Mode
- Baselines multi-rota
- Image-to-code (visão sob demanda via Ollama)
- Pool/lifecycle seguro do Chromium
- Cancelamento de comparação via SSE
- Providers: Text / Vision / Embedding separados

---

## 5. Decisão arquitetural (não criar monólito artificial)

Não vamos inventar `apps/desktop` + `modules/*` vazios. O Forge já tem forma clara:

```text
ia_platform/
  visual_engine/          # API Python (fachada, segurança, modelos, bridge)
  server.py               # rotas /api/visual/*
  dev_server.py           # URL local do preview
  static/                 # UI Comparação (fases 2+)

visual_engine/            # Pacote Node ESM (núcleo Puppeteer/pixelmatch)
  src/                    # browser, capture, comparison, dom, cli

local_agent/
  checkpoint.py           # já existe — usado pelo correction loop
  (futuro) tools/visual_* # tool fina para o agente
```

**Por que Node no núcleo:** reaproveitar `puppeteer-core` + Chrome do Windows sem reescrever tudo; o Forge continua Python.  
**Por que não embutir o Express:** um único processo HTTP (Forge :8787).

Contrato interno (Python ↔ Node CLI JSON):

```json
{
  "op": "compare" | "capture" | "compare_images",
  "source": {"type": "url|image|artifact", "value": "..."},
  "target": {"type": "url|image|artifact", "value": "..."},
  "viewport": {"width": 1366, "height": 768, "deviceScaleFactor": 1},
  "options": {"threshold": 0.1, "fullPage": true, "waitMs": 1500, "includeDomDiff": true}
}
```

---

## 6. Plano por fases

| Fase | Entrega | Critério de saída |
|------|---------|-------------------|
| **0** | Diagnóstico + inventário + este doc | Plano revisável |
| **1** | Núcleo: browser, capture, pixelmatch, presets, artefatos, testes unitários | `npm test` + pytest sem Chrome opcional |
| **2** | Rotas Forge URL×URL + imagem×imagem + histórico básico + UI mínima | Capture local + compare |
| **3** | Mockup×URL + normalização + overlay | Relatório JSON |
| **4** | DOM/layout + correlação região↔elemento | Diff tipado |
| **5** | Correction loop + checkpoint/rollback | Piora → rollback |
| **6** | Pixel Perfect Mode multi-viewport | Metas + estagnação |
| **7** | Baselines / regressão multi-rota | Approve/reject |
| **8** | Pool browser, cleanup, telemetria, docs finais | Aceitação §30 |

---

## 7. Riscos técnicos

| Risco | Mitigação |
|-------|-----------|
| Chromium órfão / vazamento | Pool com timeout + `finally` close + job cleanup |
| SSRF (URL arbitrária) | Allowlist: preview Forge + localhost de sessão + http(s) externos opcionais |
| Localhost bloqueado no código legado | Reescrever validator (permitir só projetos controlados) |
| Dual runtime Node+Python | Bridge CLI estável; Node opcional (`[visual]` extra) |
| Concorrência viewport na mesma Page | Sequencial ou 1 page/viewport |
| Crop silencioso engana score | Normalização explícita + warning de proporção |
| VRAM 8GB + modelo visão | Carregar visão sob demanda; unload após análise |
| Porta 3000 vs 8787 | Só Forge; Node sem listen |
| Path traversal em artefatos | Reusar `resolve_in_workspace` |
| `main` atrasado vs hardening | Branch baseada no tip do Forge atual |

---

## 8. Dependências

| Ação | Pacote |
|------|--------|
| **Manter (Forge)** | Python stdlib, Ollama HTTP |
| **Adicionar (Node `visual_engine/`)** | `puppeteer-core`, `pixelmatch`, `pngjs`, `jsdom`, `diff-dom` |
| **Adicionar (Python opcional)** | nenhuma obrigatória na Fase 1; Pillow opcional depois |
| **Não trazer** | express, cors, helmet, winston, nodemon (app antigo) |
| **Descartar do deploy Forge** | Docker do Compare, SQLite próprio, UI public/ |

---

## 9. Arquivos provavelmente tocados (migração completa)

- `visual_engine/**` (novo)
- `ia_platform/visual_engine/**` (novo)
- `ia_platform/server.py` (rotas)
- `ia_platform/static/{index.html,app.js,app.css}` (aba Comparação)
- `ia_platform/dev_server.py` (URL para capture)
- `local_agent/checkpoint.py` / agent loop (Fase 5)
- `pyproject.toml` / docs / `.env.example`
- `docs/VISUAL_*.md`

---

## 10. Pergunta bloqueadora

**Nenhuma bloqueadora restante.** O repositório `puppeteer-compare` foi analisado (clone `master`). Localhost precisa ser permitido para preview — isso é decisão de produto já implícita no brief e será implementada na segurança do Visual Engine.
