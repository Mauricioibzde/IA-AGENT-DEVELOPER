#!/usr/bin/env bash
# Publica o projeto completo em https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPO_URL="https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git"

echo "=== Publicar projeto no GitHub ==="
echo "Pasta: $ROOT"
echo "Repo:  $REPO_URL"

if [[ ! -d .git ]]; then
  git init
  git checkout -b main
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

git checkout main 2>/dev/null || git checkout -b main

git add -A
git reset -- projects 2>/dev/null || true
git reset -- sandbox 2>/dev/null || true

if [[ -n "$(git status --porcelain)" ]]; then
  git commit -m "feat: publish full Forge platform (auto-setup, UI, local_agent)"
else
  echo "Nada novo para commitar."
fi

if command -v gh >/dev/null 2>&1; then
  gh auth status >/dev/null 2>&1 || gh auth login -h github.com -p https -w
  gh auth setup-git >/dev/null 2>&1 || true
fi

echo "Enviando para o GitHub..."
if ! git push -u origin main; then
  echo "Tentando --force-with-lease..."
  git push -u origin main --force-with-lease
fi

echo ""
echo "SUCESSO: https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER"
