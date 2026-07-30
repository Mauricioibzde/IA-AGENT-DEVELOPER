# Correction Loop

Reutiliza `local_agent/checkpoint.py` para rollback seguro.

```text
COMPARE (baseline)
→ enquanto tentativas < max e score < meta:
    PLAN PATCH
      - strategy=css → heurística CSS (layout/regions)
      - strategy=agent → goal CodingAgent (bootstrap/refine a partir do mockup)
      - strategy=hybrid → agente se longe; CSS se perto
    → CHECKPOINT
    → APPLY PATCH (CSS overrides ou run do agente)
    → COMPARE again
    → se piorou: ROLLBACK
    → se melhorou: ACCEPT
    → se estagnou N vezes: STOP
→ COMPLETED | CANCELLED | FAILED
```

## API

| Método | Rota | Função |
|--------|------|--------|
| POST | `/api/projects/:id/visual/correction/start` | Inicia loop (body: `mockup`, metas, `strategy`) |
| GET | `/api/projects/:id/visual/correction` | Job ativo |
| GET | `/api/projects/:id/visual/correction/:id` | Status + tentativas + eventos |
| POST | `/api/projects/:id/visual/correction/:id/cancel` | Cancela |

### Body de start (exemplo)

```json
{
  "mockup": "mockups/home.png",
  "strategy": "agent",
  "target_similarity": 0.95,
  "max_attempts": 4,
  "max_agent_steps": 12,
  "min_improvement": 0.005,
  "stagnation_limit": 2,
  "viewport": { "width": 1366, "height": 768 },
  "fit": "contain"
}
```

`strategy`: `css` (padrão legado) · `agent` (mockup→código) · `hybrid`.

Veja também `docs/IMAGE_TO_CODE.md`.
## Eventos (em `correction.events`)

`correction.started` · `comparison.completed` · `correction.planning` ·  
`correction.patch_created` · `correction.applied` · `correction.retesting` ·  
`correction.improved` · `correction.rolled_back` · `correction.completed` ·  
`correction.cancelled` · `comparison.failed`

## Patches

Fase 5 usa patches **heurísticos** (CSS em `correction-overrides.css` + link em `index.html`), derivados de `layoutChanges` e regiões com `confidence` high/medium.

Patches que **pioram** a similaridade são revertidos automaticamente via checkpoint.

## Limites conhecidos

- `strategy=css` não substitui um modelo de código/visão completo.
- `strategy=agent|hybrid` usa o CodingAgent + diffs do Visual Engine (ver `IMAGE_TO_CODE.md`).
- Heurística CSS pode ser insuficiente para mudanças estruturais grandes.
- Comparações reais no loop exigem Node + Chrome + preview acessível.
