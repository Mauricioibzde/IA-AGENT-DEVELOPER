#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot: setup + start local platform (finish project today flow).
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "=== IA Agent Developer — Start Today ===" -ForegroundColor Green

# Setup if needed
if (-not (Test-Path (Join-Path $Root ".venv")) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Install Python 3.11+ first."
}

Write-Host "1/3 Running setup..." -ForegroundColor Cyan
& "$Root\scripts\setup.ps1" -SkipSmoke

Write-Host "2/3 Running tests..." -ForegroundColor Cyan
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Error "Tests failed"; exit 1 }

Write-Host "3/3 Starting web platform..." -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:8787 in your browser" -ForegroundColor Yellow
& "$Root\scripts\run-platform.ps1"
