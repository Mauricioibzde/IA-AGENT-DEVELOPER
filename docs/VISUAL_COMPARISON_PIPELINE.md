# Visual Comparison Pipeline

> Evolutivo — detalhado nas Fases 2–4.

```text
request → validate URL/path → launch browser (pool) → stabilize → capture
       → normalize images → pixelmatch → (dom/layout) → report.json → SSE
```

Modos: `url-vs-url` · `image-vs-image` · `mockup-vs-url` · baseline · before/after.

Ver `docs/VISUAL_ENGINE.md` e `docs/MIGRATION_FROM_PUPPETEER_COMPARE.md`.
