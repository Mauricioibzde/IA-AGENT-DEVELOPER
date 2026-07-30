# Visual Engine — Forge

Módulo interno de captura, comparação visual e (futuro) loop de correção.

## Papel

O Visual Engine **não** é um segundo produto. Ele é chamado pelo Forge para:

1. Capturar o preview local (ou URL permitida)
2. Comparar contra outra URL, imagem ou mockup
3. Produzir artefatos + relatório JSON consumível pela IA
4. (Fases 5+) alimentar o correction loop com scores e rollback

## Layout

```text
visual_engine/                 # Node ESM — núcleo (Puppeteer / pixelmatch)
  package.json
  src/
    browser.js                 # launch / close / Chrome detect (Windows-first)
    capture.js                 # screenshot determinístico
    stabilize.js               # CSS anti-animação
    compareImages.js           # pixelmatch + normalização
    viewports.js               # DEVICE_PRESETS
    artifacts.js               # paths seguros
    cli.js                     # stdin/argv JSON → stdout JSON
  tests/

ia_platform/visual_engine/     # Python — fachada usada pelo server/agente
  models.py                    # dataclasses / schemas do relatório
  security.py                  # URL allowlist (preview + projeto)
  bridge.py                    # subprocess → node cli
  service.py                   # compare / capture API
```

## Contrato Python

```python
from ia_platform.visual_engine import VisualEngine, CompareRequest, Side

engine = VisualEngine(project_dir)
report = engine.compare(
    CompareRequest(
        source=Side(type="url", value="http://127.0.0.1:9200/"),
        target=Side(type="image", value="mockups/home.png"),
        viewport={"width": 1366, "height": 768},
        options={"threshold": 0.1, "includeDomDiff": True},
    )
)
# report.similarity, report.artifacts, report.regions, ...
```

## Artefatos

```text
projects/<projectId>/.agent/visual/<comparisonId>/
  reference.png
  actual.png
  diff.png
  report.json
  metadata.json
```

Baselines (Fase 7): `.agent/visual/baselines/<route-id>/`.

## Eventos SSE (planejados)

`comparison.started` · `browser.launching` · `page.ready` · `screenshot.captured` ·  
`comparison.processing` · `comparison.completed` · `comparison.failed` · `correction.*`

## Requisitos de runtime

- Node.js ≥ 18
- Chrome/Chromium instalado (paths Windows detectados automaticamente)
- Variável opcional: `CHROME_EXECUTABLE_PATH` / `PUPPETEER_EXECUTABLE_PATH`

Instalação do núcleo:

```bash
cd visual_engine && npm install
```

## Segurança (resumo)

- Só `http:` / `https:`
- `localhost` / `127.0.0.1` **somente** se a porta for sessão de preview do projeto ou allowlist explícita
- Paths de imagem resolvidos via `resolve_in_workspace`
- Sem `file://` arbitrário
- Timeout e cancelamento obrigatórios

Ver também: `docs/SECURITY.md` (evolutivo), `docs/ARTIFACTS.md`.

## API Forge (Fase 2)

| Método | Rota | Função |
|--------|------|--------|
| GET | `/api/projects/:id/visual/status` | Node/Chrome disponíveis |
| GET | `/api/projects/:id/visual/comparisons` | Histórico |
| GET | `/api/projects/:id/visual/comparisons/:cid` | Relatório |
| GET | `/api/projects/:id/visual/comparisons/:cid/:file` | Artefato PNG/JSON |
| POST | `/api/projects/:id/visual/capture` | Captura preview ou URL |
| POST | `/api/projects/:id/visual/compare` | Compare unificado |
| POST | `/api/projects/:id/visual/mockup` | Upload de mockup → `mockups/` |
| DELETE | `/api/projects/:id/visual/comparisons/:cid` | Remove comparação |

### Normalização (Fase 3)

`options.fit`: `contain` (padrão) · `cover` · `crop` · `none`

Artefatos extras: `overlay.png`, `reference-normalized.png`, `actual-normalized.png`.

UI: upload de mockup (converte para PNG no browser), views lado a lado / diff / overlay / slider.

### Análises separadas (Fase 4)

| Análise | Artefato / campo | Conteúdo |
|---------|------------------|----------|
| Pixel Diff | `diff.png`, `similarity` | pixelmatch |
| DOM Diff | `dom-diff.json`, `domChanges` | nós add/remove/texto/atributos |
| Layout Diff | `layout-diff.json`, `layoutChanges` | retângulos / posição / tamanho |
| Style Diff | `styleChanges` | color, background, fontSize, … |
| Regiões | `regions[]` | bbox + severidade + elemento provável (`confidence`) |

Correlação região↔elemento usa IoU/overlap e **nunca** afirma match exato sem `confidence`.

Atalhos no body de `compare`:

- `{ "url1", "url2" }` — legado puppeteer-compare
- `{ "mockup": "mockups/home.png" }` — mockup × preview
- `{ "preview_vs_url": "https://…" }` — preview × URL

UI: aba **Comparação** no painel direito (`?v=20`).

## Fases

Ver `docs/MIGRATION_FROM_PUPPETEER_COMPARE.md`.
