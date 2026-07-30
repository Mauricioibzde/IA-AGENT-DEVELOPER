# Image-to-Code

Fluxo operacional no Forge (estratégia `agent` / `hybrid` do correction loop):

```text
UPLOAD mockup
→ VISION (opcional): LLaVA / Qwen2-VL descreve o PNG → especificação UI
→ COMPARE preview × mockup (baseline)
→ enquanto tentativas < max e score < meta:
    se UI ainda distante → AGENT bootstrap (implementar a partir do mockup + visão)
    senão → AGENT refine (com feedback de layout/regiões + lembrete visual)
       ou, no híbrido, PATCH CSS heurístico quando já estiver perto
    → COMPARE again
    → se piorou: ROLLBACK (checkpoint)
    → se melhorou: ACCEPT
→ COMPLETED | CANCELLED | FAILED
```

## Como funciona

1. Você envia o PNG do mockup.
2. **Visão** (LLaVA / Qwen2-VL / Llama 3.2 Vision) descreve layout, tipografia, cores e hierarquia do PNG quando `use_vision` está ativo e um modelo de visão está instalado no Ollama.
3. O Visual Engine compara o mockup com o preview do projeto (score estrutural + pixel).
4. Em `hybrid` (padrão):
   - Se ainda **não há UI** (score baixo), o agente **cria/reescreve** HTML/CSS/JS usando a especificação visual + diffs.
   - Depois entra no modo de **refino** (ajustes pontuais).
5. Em `agent`: só o agente de código (sem patches CSS automáticos).
6. Em `css`: só patches CSS do Visual Engine (rápido, limitado; sem visão).
7. Em cada iteração: aplica → espera settle do preview → compara de novo → decide se continua.
8. Para quando o score ≥ alvo, ou esgota iterações / orçamento.

### Visão (ver o mockup de verdade)

Sem um modelo de visão, o agente só recebe métricas do Visual Engine (bounding boxes, cores amostradas). Com visão:

- O PNG é enviado ao Ollama (`/api/chat` com `images`).
- A resposta vira uma **especificação UI em português** injetada no goal do CodingAgent.
- Cache em `.agent/vision-cache/` (por mockup + modelo + mtime).
- Eventos: `vision.started` → `vision.completed` / `vision.cached`, ou `vision.skipped` / `vision.failed`.

Instale um modelo, por exemplo:

```bash
ollama pull llava
# ou: ollama pull qwen2.5-vl
# ou: ollama pull llama3.2-vision
```

Na API: `"use_vision": true` (já ligado na UI para hybrid/agent). Opcional: `"vision_model": "llava"`.

## Como usar na UI

1. Abra **Visual → Comparação**
2. Envie/informe o mockup (`mockups/...`)
3. Clique em **Mockup → Código**
4. Acompanhe tentativas no painel *Correction loop* (status ao vivo inclui análise de visão)
5. Use **Interromper** para cancelar

Estratégias:
- `hybrid` (padrão recomendado) — agente quando longe; CSS fino quando perto; reescala para agente periodicamente
- `agent` — cada tentativa pede ao CodingAgent gerar/ajustar código
- `css` — apenas patches heurísticos (botão **Corrigir CSS**)

Melhorias do loop:
- Visão: JSON estruturado (cores/layout/componentes), resize via ffmpeg, cache versionado, reanálise se estagnar
- checklist prioritário a partir de regiões/layout (bbox, texto, styleChanges)
- inventário de arquivos + detecção de stack (HTML/React)
- espera de settle do preview antes de recomparar
- híbrido só aplica CSS mensurável quando similarity ≥ ~82%
- barra de progresso, status ao vivo e preview da especificação visual
- após upload do mockup, CTA **Mockup → Código** + toggle/modelo de visão

## API

`POST /api/projects/:id/visual/correction/start`

```json
{
  "mockup": "mockups/home.png",
  "strategy": "hybrid",
  "target_similarity": 0.95,
  "max_attempts": 5,
  "max_agent_steps": 14,
  "use_vision": true,
  "vision_model": "llava",
  "stack": "html",
  "preview_mode": "auto",
  "viewport": { "width": 1366, "height": 768 }
}
```

| Campo | Tipo | Padrão | Notas |
|-------|------|--------|-------|
| `strategy` | string | `css` | `css` · `agent` · `hybrid` · aliases `mockup-to-code` / `image-to-code` → `agent` |
| `use_vision` | bool | `true` | Analisa o mockup com modelo de visão Ollama (agent/hybrid) |
| `vision_model` | string | auto | Ex.: `llava`, `qwen2.5-vl` |

## Limites

- Exige Ollama + modelo coder instalado para `agent`/`hybrid`.
- Visão exige um modelo multimodal instalado; se faltar, o loop segue só com diffs do Visual Engine.
- Comparações reais exigem Visual Engine (Node/Chrome) e preview acessível.
- O loop não substitui revisão humana em mudanças estruturais grandes.
