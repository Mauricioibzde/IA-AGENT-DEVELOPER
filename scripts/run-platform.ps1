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
$Port = 8787

function Stop-ListenerOnPort {
    param([int]$ListenPort)
    $stopped = $false
    try {
        $connections = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            $procId = $conn.OwningProcess
            if ($procId -and $procId -ne 0) {
                Write-Host "Stopping old platform on port $ListenPort (PID $procId)..." -ForegroundColor Yellow
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                $stopped = $true
            }
        }
    } catch {
        $lines = netstat -ano | Select-String ":$ListenPort\s" | Select-String "LISTENING"
        foreach ($line in $lines) {
            $parts = ($line -replace '\s+', ' ').ToString().Trim().Split(' ')
            $procId = $parts[-1]
            if ($procId -match '^\d+$') {
                Write-Host "Stopping old platform on port $ListenPort (PID $procId)..." -ForegroundColor Yellow
                taskkill /PID $procId /F 2>$null | Out-Null
                $stopped = $true
            }
        }
    }
    if ($stopped) { Start-Sleep -Seconds 1 }
}

Stop-ListenerOnPort -ListenPort $Port

Write-Host "Checking Ollama..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 3 | Out-Null
    Write-Host "Ollama OK" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Ollama not reachable. Use 'Configurar automaticamente' in the UI or run 'ollama serve'." -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root "sandbox") | Out-Null
Write-Host "Starting Forge Platform v2 at http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Verify setup API: http://127.0.0.1:$Port/api/health -> full_setup_stream: true" -ForegroundColor DarkGray
$env:PYTHONPATH = $Root
python "$Root\ia_platform\server.py" --host 127.0.0.1 --port $Port
