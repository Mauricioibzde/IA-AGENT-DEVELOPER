#!/usr/bin/env bash
# Installs and configures IA Agent Developer on Linux/macOS.
# Usage:
#   bash scripts/setup.sh
#   MODEL=qwen2.5-coder:7b bash scripts/setup.sh
#   bash scripts/setup.sh --skip-smoke

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="${MODEL:-${OLLAMA_MODEL:-qwen2.5-coder:7b}}"
OLLAMA_HOST_URL="${OLLAMA_HOST:-http://127.0.0.1:11434}"
WORKSPACE="${WORKSPACE:-sandbox}"
SKIP_OLLAMA_INSTALL=0
SKIP_MODEL_PULL=0
SKIP_SMOKE=0
SKIP_TESTS=0

for arg in "$@"; do
  case "$arg" in
    --skip-ollama-install) SKIP_OLLAMA_INSTALL=1 ;;
    --skip-model-pull) SKIP_MODEL_PULL=1 ;;
    --skip-smoke) SKIP_SMOKE=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    --model=*) MODEL="${arg#*=}" ;;
    --workspace=*) WORKSPACE="${arg#*=}" ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

step() {
  printf '\n==> %s\n' "$1"
}

have() {
  command -v "$1" >/dev/null 2>&1
}

pick_python() {
  local candidate
  for candidate in python3 python; do
    if have "$candidate"; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  echo "Python 3.10+ is required." >&2
  exit 1
}

ollama_ready() {
  curl -fsS --max-time 3 "$OLLAMA_HOST_URL/api/tags" >/dev/null 2>&1
}

ensure_ollama_installed() {
  if have ollama; then
    echo "Ollama already installed."
    return 0
  fi
  if [[ "$SKIP_OLLAMA_INSTALL" -eq 1 ]]; then
    echo "Ollama is not installed and --skip-ollama-install was set." >&2
    exit 1
  fi
  echo "Installing Ollama via official script..."
  curl -fsSL https://ollama.com/install.sh | sh
  if ! have ollama; then
    echo "Ollama install finished, but 'ollama' is not on PATH. Open a new shell and re-run setup." >&2
    exit 1
  fi
}

ensure_ollama_running() {
  if ollama_ready; then
    echo "Ollama API is reachable at $OLLAMA_HOST_URL"
    return 0
  fi
  echo "Starting ollama serve in background..."
  nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  local i
  for i in $(seq 1 30); do
    sleep 1
    if ollama_ready; then
      echo "Ollama is ready."
      return 0
    fi
  done
  echo "Could not reach Ollama at $OLLAMA_HOST_URL. Check /tmp/ollama-serve.log" >&2
  exit 1
}

echo "IA Agent Developer setup"
echo "Root: $ROOT"
echo "Model: $MODEL"
echo "Ollama: $OLLAMA_HOST_URL"

step "Checking Python"
PYTHON="$(pick_python)"
echo "Using: $PYTHON"
"$PYTHON" --version

step "Installing Python project dependencies"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e ".[dev]"

step "Ensuring Ollama"
ensure_ollama_installed
ensure_ollama_running

if [[ "$SKIP_MODEL_PULL" -eq 0 ]]; then
  step "Pulling model '$MODEL'"
  ollama pull "$MODEL"
else
  echo "Skipping model pull."
fi

step "Creating workspace '$WORKSPACE'"
mkdir -p "$ROOT/$WORKSPACE"

export OLLAMA_HOST="$OLLAMA_HOST_URL"
export OLLAMA_MODEL="$MODEL"

if [[ "$SKIP_TESTS" -eq 0 ]]; then
  step "Running unit tests"
  "$PYTHON" -m pytest -q
fi

if [[ "$SKIP_SMOKE" -eq 0 ]]; then
  step "Running dry-run smoke test"
  "$PYTHON" ./ollama_agent.py \
    --workspace "$WORKSPACE" \
    --model "$MODEL" \
    --dry-run \
    --verbose \
    "Create a file called demo.txt with the content hello"
fi

cat <<EOF

Setup complete.

Next commands:
  $PYTHON ollama_agent.py --workspace ./$WORKSPACE --model $MODEL --verbose "Create a file called demo.txt with the content hello"
  $PYTHON ollama_agent.py --workspace ./$WORKSPACE --model $MODEL "Create a python starter project called demo_py in folder demo_py"
  $PYTHON verify_agent.py --verbose
EOF
