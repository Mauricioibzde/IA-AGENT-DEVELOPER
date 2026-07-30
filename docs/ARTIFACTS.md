# Artefatos do Visual Engine

```text
projects/<projectId>/.agent/visual/<comparisonId>/
  reference.png
  actual.png
  diff.png
  report.json
  metadata.json

projects/<projectId>/.agent/visual/baselines/<routeId>/
  baseline.png
  meta.json

projects/<projectId>/.agent/visual/suites/<suiteRunId>/
  report.json
```

- IDs sanitizados (`safeId`)
- Path traversal rejeitado
- Baselines em `.agent/visual/baselines/` — **não** apagar no cleanup automático
- Retenção: `POST …/visual/cleanup` (idade + contagem); baselines/corrections protegidas
- Stats: `GET …/visual/cleanup`

Servir via Forge: `GET /api/projects/<id>/visual/comparisons/<comparisonId>/<file>`  
Baselines: `GET /api/projects/<id>/visual/baselines/<routeId>/baseline.png`

Ver `docs/BASELINES.md`.
