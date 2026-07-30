# Correction Loop

Reutiliza `local_agent/checkpoint.py` para rollback seguro.

```text
COMPARE (baseline)
→ enquanto tentativas < max e score < meta:
    PLAN PATCH (heurístico a partir de layout/regions)
    → CHECKPOINT
    → APPLY PATCH (CSS overrides)
    → COMPARE again
    → se piorou: ROLLBACK
    → se melhorou: ACCEPT
    → se estagnou N vezes: STOP
→ COMPLETED | CANCELLED | FAILED
```

## API

| Método | Rota | Função |
|--------|------|--------|
| POST | `/api/projects/:id/visual/correction/start` | Inicia loop (body: `mockup`, metas) |
| GET | `/api/projects/:id/visual/correction` | Job ativo |
| GET | `/api/projects/:id/visual/correction/:id` | Status + tentativas + eventos |
| POST | `/api/projects/:id/visual/correction/:id/cancel` | Cancela |

### Body de start (exemplo)

```json
{
  "mockup": "mockups/home.png",
  "target_similarity": 0.95,
  "max_attempts": 5,
  "min_improvement": 0.005,
  "stagnation_limit": 2,
  "viewport": { "width": 1366, "height": 768 },
  "fit": "contain"
}
```

## Eventos (em `correction.events`)

`correction.started` · `comparison.completed` · `correction.planning` ·  
`correction.patch_created` · `correction.applied` · `correction.retesting` ·  
`correction.improved` · `correction.rolled_back` · `correction.completed` ·  
`correction.cancelled` · `comparison.failed`

## Patches

Fase 5 usa patches **heurísticos** (CSS em `correction-overrides.css` + link em `index.html`), derivados de `layoutChanges` e regiões com `confidence` high/medium.

Patches que **pioram** a similaridade são revertidos automaticamente via checkpoint.

## Limites conhecidos

- Não substitui um modelo de código/visão completo (Fase image-to-code / agente).
- Heurística CSS pode ser insuficiente para mudanças estruturais grandes.
- Comparações reais no loop exigem Node + Chrome + preview acessível.
