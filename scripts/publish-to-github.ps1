#Requires -Version 5.1
<#
.SYNOPSIS
  Publica TODO o projeto Forge/IA-AGENT-DEVELOPER no GitHub.

.DESCRIPTION
  Usa o conteúdo da pasta atual (workspace) e envia para:
  https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git

  Execute no PowerShell, dentro da pasta do projeto:
    powershell -ExecutionPolicy Bypass -File .\scripts\publish-to-github.ps1

.NOTES
  Precisa estar logado no GitHub (gh auth login) OU ter credenciais Git configuradas.
#>
$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host ""
Write-Host "=== Publicar projeto no GitHub ===" -ForegroundColor Cyan
Write-Host "Pasta: $Root"
Write-Host "Repo:  $RepoUrl"
Write-Host ""

# Garantir que é um repo git
if (-not (Test-Path (Join-Path $Root ".git"))) {
    Write-Host "Inicializando git..." -ForegroundColor Yellow
    git init
    git checkout -b main
}

# Remote correto
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0 -or -not $existing) {
    git remote add origin $RepoUrl
    Write-Host "Remote origin adicionado." -ForegroundColor Green
} else {
    git remote set-url origin $RepoUrl
    Write-Host "Remote origin atualizado para $RepoUrl" -ForegroundColor Green
}

# Branch main
git checkout main 2>$null
if ($LASTEXITCODE -ne 0) {
    git checkout -b main
}

# Ignorar pastas de trabalho locais
$ignoreFile = Join-Path $Root ".gitignore"
if (Test-Path $ignoreFile) {
    $ignoreText = Get-Content $ignoreFile -Raw
    if ($ignoreText -notmatch "(?m)^projects/") {
        Add-Content $ignoreFile "`nprojects/`n"
    }
    if ($ignoreText -notmatch "(?m)^sandbox/") {
        Add-Content $ignoreFile "`nsandbox/`n"
    }
}

Write-Host "Adicionando arquivos do projeto..." -ForegroundColor Cyan
git add -A
# Não versionar projetos gerados / sandbox
git reset -- projects 2>$null
git reset -- sandbox 2>$null

$status = git status --porcelain
if ($status) {
    Write-Host "Criando commit..." -ForegroundColor Cyan
    git commit -m "feat: publish full Forge platform (auto-setup, UI, local_agent)"
} else {
    Write-Host "Nada novo para commitar (já está commitado)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Enviando para o GitHub (pode pedir login)..." -ForegroundColor Cyan
Write-Host ""

# Preferir gh se disponível (abre login no browser se preciso)
$pushed = $false
if (Get-Command gh -ErrorAction SilentlyContinue) {
    $auth = gh auth status 2>&1 | Out-String
    if ($auth -notmatch "Logged in") {
        Write-Host "Fazendo login no GitHub via gh..." -ForegroundColor Yellow
        gh auth login -h github.com -p https -w
    }
    gh auth setup-git 2>$null
}

git push -u origin main
if ($LASTEXITCODE -eq 0) {
    $pushed = $true
} else {
    Write-Host ""
    Write-Host "Push normal falhou. Tentando com --force-with-lease..." -ForegroundColor Yellow
    git push -u origin main --force-with-lease
    if ($LASTEXITCODE -eq 0) { $pushed = $true }
}

if (-not $pushed) {
    Write-Host ""
    Write-Host "FALHOU o push. Faça login e tente de novo:" -ForegroundColor Red
    Write-Host "  gh auth login" -ForegroundColor Yellow
    Write-Host "  git push -u origin main" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Ou use um Personal Access Token:" -ForegroundColor Yellow
    Write-Host "  https://github.com/settings/tokens" -ForegroundColor DarkGray
    exit 1
}

Write-Host ""
Write-Host "SUCESSO! Repositorio atualizado:" -ForegroundColor Green
Write-Host "  https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER" -ForegroundColor Green
Write-Host ""
Write-Host "Confira se aparecem as pastas: ia_platform, local_agent, scripts" -ForegroundColor DarkGray
Write-Host ""
