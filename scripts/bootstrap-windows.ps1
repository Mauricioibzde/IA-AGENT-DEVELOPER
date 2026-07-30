#Requires -Version 5.1
<#
.SYNOPSIS
  Clone/update the Forge branch on Windows and start the local platform.

.DESCRIPTION
  Use this on YOUR Windows PC (not inside the Cloud Agent).
  - Clones the repo if missing
  - Checks out cursor/mockup-to-code-loop-40ee
  - Installs Python deps + visual_engine npm deps
  - Ensures Ollama is running
  - Starts Forge at http://127.0.0.1:8787

.EXAMPLE
  # First time (from any folder):
  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1 -CloneIfMissing

.EXAMPLE
  # Already inside the repo:
  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1
#>

[CmdletBinding()]
param(
    [string]$RepoUrl = "https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git",
    [string]$Branch = "cursor/mockup-to-code-loop-40ee",
    [string]$TargetDir = (Join-Path $HOME "IA-AGENT-DEVELOPER"),
    [string]$Model = "deepseek-coder:6.7b",
    [string]$VisionModel = "moondream",
    [switch]$CloneIfMissing,
    [switch]$SkipVisionPull,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-Command([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Comando nao encontrado: $Name. $Hint"
    }
}

Write-Host "Forge — bootstrap Windows (local)" -ForegroundColor Green
Write-Host "Branch: $Branch"
Write-Host "Pasta:  $TargetDir"

Assert-Command "git" "Instale Git: https://git-scm.com/download/win"
Assert-Command "python" "Instale Python 3.11+ e marque Add to PATH: https://www.python.org/downloads/"
Assert-Command "node" "Instale Node.js 18+: https://nodejs.org/"
Assert-Command "npm" "Instale Node.js 18+ (inclui npm)."

$inRepo = Test-Path (Join-Path (Get-Location) "ia_platform\server.py")
if ($inRepo) {
    $Root = (Resolve-Path ".").Path
    Write-Host "Usando repositorio atual: $Root"
} elseif ((Test-Path (Join-Path $TargetDir "ia_platform\server.py"))) {
    $Root = (Resolve-Path $TargetDir).Path
    Set-Location $Root
    Write-Host "Usando repositorio existente: $Root"
} elseif ($CloneIfMissing) {
    Write-Step "Clonando repositorio"
    $parent = Split-Path -Parent $TargetDir
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    if (Test-Path $TargetDir) {
        throw "Pasta ja existe mas nao parece o repo: $TargetDir"
    }
    git clone --branch $Branch --single-branch $RepoUrl $TargetDir
    $Root = (Resolve-Path $TargetDir).Path
    Set-Location $Root
} else {
    throw @"
Repositorio nao encontrado.

Opcao A — clone automatico:
  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1 -CloneIfMissing

Opcao B — clone manual e depois rode este script dentro da pasta:
  git clone -b $Branch $RepoUrl `"$TargetDir`"
  cd `"$TargetDir`"
  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1
"@
}

Write-Step "Atualizando branch $Branch"
git fetch origin $Branch
git checkout $Branch
git pull origin $Branch

Write-Step "Setup Python / Ollama"
& "$Root\scripts\setup.ps1" -Model $Model -SkipSmoke -SkipTests

Write-Step "Dependencias do Visual Engine (Node)"
Push-Location (Join-Path $Root "visual_engine")
try {
    npm install --omit=dev
} finally {
    Pop-Location
}

if (-not $SkipVisionPull) {
    Write-Step "Baixando modelo de visao ($VisionModel) — opcional, pode demorar"
    try {
        ollama pull $VisionModel
    } catch {
        Write-Host "Aviso: nao foi possivel puxar $VisionModel. Continuar sem visao." -ForegroundColor Yellow
    }
}

if ($NoStart) {
    Write-Host ""
    Write-Host "Bootstrap concluido. Para iniciar:" -ForegroundColor Green
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run-platform.ps1"
    Write-Host "Depois abra: http://127.0.0.1:8787"
    exit 0
}

Write-Step "Iniciando Forge em http://127.0.0.1:8787"
Write-Host "Deixe este terminal aberto. Pare com Ctrl+C." -ForegroundColor Yellow
& "$Root\scripts\run-platform.ps1"
