#Requires -Version 5.1
<#
.SYNOPSIS
  One-liner helper: clone Forge to %USERPROFILE%\IA-AGENT-DEVELOPER and bootstrap.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/Mauricioibzde/IA-AGENT-DEVELOPER/cursor/mockup-to-code-loop-40ee/scripts/get-forge-windows.ps1 | iex"
#>

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git"
$Branch = "cursor/mockup-to-code-loop-40ee"
$TargetDir = Join-Path $HOME "IA-AGENT-DEVELOPER"

Write-Host "Baixando Forge para $TargetDir (branch $Branch)..." -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git nao encontrado. Instale: https://git-scm.com/download/win"
}

if (-not (Test-Path (Join-Path $TargetDir "ia_platform\server.py"))) {
    if (Test-Path $TargetDir) {
        throw "Pasta existe mas nao e o repositorio: $TargetDir"
    }
    git clone --branch $Branch --single-branch $RepoUrl $TargetDir
} else {
    Write-Host "Repositorio ja existe — atualizando..."
}

Set-Location $TargetDir
& "$TargetDir\scripts\bootstrap-windows.ps1"
