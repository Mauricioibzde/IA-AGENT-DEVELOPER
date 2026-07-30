# Visual Comparison Pipeline

> Evolutivo — detalhado nas Fases 2–4.

```text
request → validate URL/path → launch browser → stabilize → capture (+layout snapshot)
       → normalize images → pixelmatch → regions
       → DOM diff (jsdom) → layout/style diff → correlate regions↔elements
       → report.json + dom-diff.json + layout-diff.json
```

Análises **não** são misturadas: `analyses.pixel|dom|layout|style` no relatório.

Modos: `url-vs-url` · `image-vs-image` · `mockup-vs-url` · baseline · before/after.

Ver `docs/VISUAL_ENGINE.md` e `docs/MIGRATION_FROM_PUPPETEER_COMPARE.md`.
