# Pixel Perfect Mode (multi-viewport)

Suite de comparações sequenciais (um viewport por vez) com meta de similaridade.

## Suites

| Id | Viewports |
|----|-----------|
| `responsive` | desktop_standard, ipad_air, iphone_15 |
| `desktop` | desktop_standard, desktop_full_hd, laptop_15 |
| `mobile` | iphone_15, iphone_se, samsung_galaxy_s24, mobile_small |
| `full` | desktop_standard, laptop_13, ipad_air, iphone_15 |

Presets alinhados a `visual_engine/src/viewports.js`.

## API

| Método | Rota | Função |
|--------|------|--------|
| GET | `/api/projects/:id/visual/suites` | Lista suites |
| POST | `/api/projects/:id/visual/compare` | Com `suite` / `pixel_perfect: true` |

### Body (exemplo)

```json
{
  "mockup": "mockups/home.png",
  "suite": "responsive",
  "pixel_perfect": true,
  "target_similarity": 0.95,
  "options": { "fit": "contain", "threshold": 0.1 }
}
```

Resposta inclui `suite` (agregado) + `report` (pior viewport / primário) + `reports[]`.

### Agregação

- `minSimilarity` / `avgSimilarity` / `maxSimilarity`
- `passedCount` / `failedCount` vs `targetSimilarity`
- `status`: `passed` | `failed` | `partial` | `error`
- Artefato: `.agent/visual/suites/<id>/report.json` + entrada no histórico

## Correction loop

Se `suite` for enviado em `correction/start`, cada tentativa usa o **pior** score da suite como `similarity` (meta + estagnação/rollback continuam iguais).

## UI

Aba **Comparação**: seletor de suite + botão **Pixel Perfect** (`?v=24`).
