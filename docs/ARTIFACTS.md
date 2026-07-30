# Artefatos do Visual Engine

```text
projects/<projectId>/.agent/visual/<comparisonId>/
  reference.png
  actual.png
  diff.png
  report.json
  metadata.json
```

- IDs sanitizados (`safeId`)
- Path traversal rejeitado
- Baselines (Fase 7) em `.agent/visual/baselines/` — **não** apagar no cleanup automático
- Retenção: idade + contagem (portar de `cleanup.js` na Fase 2)

Servir via Forge: `GET /api/projects/<id>/visual/<comparisonId>/<file>` (Fase 2).
