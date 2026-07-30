# Correction Loop

> Planejado na Fase 5. Reutiliza `local_agent/checkpoint.py`.

```text
GENERATE → RUN → CAPTURE → COMPARE → DIAGNOSE → CHECKPOINT → PATCH → RETEST → ACCEPT|ROLLBACK
```

Limites: max tentativas, meta de similaridade, estagnação, piora → rollback automático.
