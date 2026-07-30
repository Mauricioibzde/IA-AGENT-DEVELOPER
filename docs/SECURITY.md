# Security — Visual Engine & Forge

## Mudança crítica vs Puppeteer Compare

O Compare **bloqueava** localhost. O Forge **precisa** de localhost para preview (`9200–9299`, `8787`).

Regra atual (`ia_platform/visual_engine/security.py`):

- Protocolos: só `http` / `https`
- Loopback: apenas portas de preview Forge / allowlist
- Imagens: `resolve_in_workspace`
- Sem `file://` arbitrário
- Metadata IPs bloqueados

## Superfícies

| Superfície | Controlo |
|------------|----------|
| URL capture | validate_compare_url |
| Uploads | tamanho + tipo (Fase 3) |
| Comandos | allowlist terminal existente |
| Artefatos | safeId + root confinement |
| Chromium | close em `finally`, timeouts |

Expandir nas Fases 2–8 (SSRF externo, upload bombs, cancelamento).
