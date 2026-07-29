#!/usr/bin/env bash
# Start local IA Agent web platform
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/sandbox"

if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama OK"
else
  echo "WARNING: Ollama not reachable. Run 'ollama serve' first."
fi

echo "Starting platform at http://127.0.0.1:8787"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$ROOT/ia_platform/server.py" --host 127.0.0.1 --port 8787
