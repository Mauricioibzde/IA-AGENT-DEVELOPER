# Aceitação — Visual Engine (Forge)

Checklist de aceite da migração puppeteer-compare → Visual Engine.

## Runtime

- [x] Node núcleo em `visual_engine/` sem Express listen
- [x] Fachada Python `ia_platform/visual_engine/`
- [x] Localhost permitido só para preview Forge (8787, 9200–9299)
- [x] Paths confinados via `resolve_in_workspace`

## Capacidades

| Capacidade | Fase | Status |
|------------|------|--------|
| Capture + pixelmatch + presets | 1–2 | OK |
| Mockup × preview + normalize/overlay | 3 | OK |
| DOM / layout / style / regiões | 4 | OK |
| Correction loop + rollback | 5 | OK |
| Pixel Perfect multi-viewport | 6 | OK |
| Baselines approve/reject | 7 | OK |
| Browser pool + cleanup + telemetria | 8 | OK |

## APIs mínimas

`status` · `capture` · `compare` · `mockup` · `comparisons` · `suites` ·  
`correction/*` · `baselines/*` · `cleanup`

## Artefatos

Comparações em `.agent/visual/<id>/`; baselines em `.agent/visual/baselines/` (protegidas do cleanup).

## Testes

```bash
cd visual_engine && npm test
python3 -m pytest ia_platform/test_correction_loop.py \
  ia_platform/test_pixel_perfect.py \
  ia_platform/test_baselines.py \
  ia_platform/test_cleanup.py \
  ia_platform/test_visual_*.py -q
```

## Fora de escopo (aceitável)

- UI glassmorphism do puppeteer-compare
- Servidor Express / SQLite próprio do Compare
- Modelo de visão Ollama (image-to-code futuro)
