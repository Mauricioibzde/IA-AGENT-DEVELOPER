# Image-to-Code

Fluxo operacional no Forge (estratégia `agent` / `hybrid` do correction loop):

```text
UPLOAD mockup
→ COMPARE preview × mockup (baseline)
→ enquanto tentativas < max e score < meta:
    se UI ainda distante → AGENT bootstrap (implementar a partir do mockup)
    senão → AGENT refine (com feedback de layout/regiões)
       ou, no híbrido, PATCH CSS heurístico quando já estiver perto
    → COMPARE again
    → se piorou: ROLLBACK (checkpoint)
    → se melhorou: ACCEPT
→ COMPLETED | CANCELLED | FAILED
```

## Como usar na UI

1. Abra **Visual → Comparação**
2. Envie/informe o mockup (`mockups/...`)
3. Clique em **Mockup → Código**
4. Acompanhe tentativas no painel *Correction loop*
5. Use **Interromper** para cancelar

Estratégias:
- `agent` — cada tentativa pede ao CodingAgent gerar/ajustar código
- `hybrid` — agente quando longe do mockup; CSS fino quando perto
- `css` — apenas patches heurísticos (botão **Corrigir CSS**)

## API

`POST /api/projects/:id/visual/correction/start`

```json
{
  "mockup": "mockups/home.png",
  "strategy": "agent",
  "target_similarity": 0.95,
  "max_attempts": 4,
  "max_agent_steps": 12,
  "stack": "html",
  "preview_mode": "auto",
  "viewport": { "width": 1366, "height": 768 }
}
```

Aliases de `strategy`: `mockup-to-code`, `image-to-code`, `i2c` → `agent`.

## Limites

- Exige Ollama + modelo coder instalado para `agent`/`hybrid`.
- Comparações reais exigem Visual Engine (Node/Chrome) e preview acessível.
- O loop não substitui revisão humana em mudanças estruturais grandes.
- Visão multimodal sob demanda (descrever o PNG via modelo de visão) continua opcional; o agente recebe o caminho do mockup + diffs do Visual Engine.
