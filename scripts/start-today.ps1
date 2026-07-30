#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot: setup + start local platform (finish project today flow).
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "=== IA Agent Developer - Start Today ===" -ForegroundColor Green

Write-Host "1/3 Running setup..." -ForegroundColor Cyan
& "$Root\scripts\setup.ps1" -SkipSmoke -SkipTests

Write-Host "2/3 Installing Visual Engine deps (if present)..." -ForegroundColor Cyan
$ve = Join-Path $Root "visual_engine"
if (Test-Path (Join-Path $ve "package.json")) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Push-Location $ve
        try { npm install --omit=dev } finally { Pop-Location }
    } else {
        Write-Host "npm not found - skipping visual_engine. Install Node.js 18+ for Visual Engine." -ForegroundColor Yellow
    }
}

Write-Host "3/3 Starting web platform..." -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:8787 in your browser" -ForegroundColor Yellow
& "$Root\scripts\run-platform.ps1"
