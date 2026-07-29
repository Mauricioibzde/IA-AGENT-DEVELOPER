#Requires -Version 5.1
<#
.SYNOPSIS
  Start the local IA Agent web platform (chat UI + API).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\run-platform.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "Checking Ollama..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 3 | Out-Null
    Write-Host "Ollama OK" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Ollama not reachable. Run 'ollama serve' in another terminal." -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root "sandbox") | Out-Null
Write-Host "Starting platform at http://127.0.0.1:8787" -ForegroundColor Green
python "$Root\ia_platform\server.py" --host 127.0.0.1 --port 8787
