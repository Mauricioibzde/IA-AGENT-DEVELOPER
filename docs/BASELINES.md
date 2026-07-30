# Baselines / regressão visual (Fase 7)

Goldens por rota sob `.agent/visual/baselines/<routeId>/`.

```text
baseline.png
meta.json          # status, viewport, sourceComparisonId, notes
```

**Não** entram no cleanup automático de comparações.

## Fluxo

```text
capturar/comparar → Aprovar (promove actual.png)
                  → Rejeitar (marca rejected; opcional remove imagem)
                  → Vs baseline (preview × golden)
```

## API

| Método | Rota | Função |
|--------|------|--------|
| GET | `/api/projects/:id/visual/baselines` | Lista |
| GET | `/api/projects/:id/visual/baselines/:route` | Detalhe |
| GET | `/api/projects/:id/visual/baselines/:route/baseline.png` | Imagem |
| POST | `/api/projects/:id/visual/baselines/approve` | Promote |
| POST | `/api/projects/:id/visual/baselines/reject` | Reject |
| POST | `/api/projects/:id/visual/baselines/compare` | Preview × baseline |
| DELETE | `/api/projects/:id/visual/baselines/:route` | Remove |

### Approve body

```json
{
  "routeId": "home",
  "comparisonId": "<id>",
  "prefer": "actual",
  "label": "Home",
  "notes": ""
}
```

Alternativa: `{ "routeId": "home", "path": "mockups/home.png" }`.

### Compare body

```json
{
  "routeId": "home",
  "target_similarity": 0.95,
  "viewport": { "width": 1366, "height": 768 },
  "options": { "fit": "contain" }
}
```

Resposta inclui `baseline.passed` além do `report` usual.

## UI

Aba **Comparação**: campo de rota + Aprovar / Rejeitar / Vs baseline (`?v=25`).
