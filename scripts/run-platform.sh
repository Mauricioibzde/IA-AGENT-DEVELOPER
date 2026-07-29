#!/usr/bin/env bash
# Start local IA Agent web platform
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT=8787

if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti tcp:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "${PIDS}" ]]; then
    echo "Stopping old platform on port ${PORT}..."
    kill ${PIDS} 2>/dev/null || true
    sleep 1
  fi
elif command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
  sleep 1
fi

if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama OK"
else
  echo "WARNING: Ollama not reachable. Use 'Configurar automaticamente' in the UI or run 'ollama serve'."
fi

echo "Starting Forge Platform v2 at http://127.0.0.1:${PORT}"
echo "Verify setup API: http://127.0.0.1:${PORT}/api/health -> full_setup_stream: true"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$ROOT/ia_platform/server.py" --host 127.0.0.1 --port "$PORT"
