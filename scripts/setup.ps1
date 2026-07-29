#Requires -Version 5.1
<#
.SYNOPSIS
  Installs and configures IA Agent Developer on Windows.

.DESCRIPTION
  Checks Python, installs project deps, ensures Ollama is available,
  pulls a coding model, creates a sandbox folder, and runs a dry-run smoke test.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

.EXAMPLE
  .\scripts\setup.ps1 -Model qwen2.5-coder:7b -SkipSmoke
#>

[CmdletBinding()]
param(
    [string]$Model = $(if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5-coder:7b" }),
    [string]$OllamaHost = $(if ($env:OLLAMA_HOST) { $env:OLLAMA_HOST } else { "http://127.0.0.1:11434" }),
    [string]$Workspace = "sandbox",
    [switch]$SkipOllamaInstall,
    [switch]$SkipModelPull,
    [switch]$SkipSmoke,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Get-PythonCommand {
    foreach ($candidate in @("python", "py", "python3")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $versionText = & $cmd --version 2>&1 | Out-String
            if ($versionText -match "Python\s+(\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                    return $cmd.Source
                }
            }
        } catch {
            continue
        }
    }
    throw "Python 3.10+ is required. Install from https://www.python.org/downloads/ and re-run setup."
}

function Test-OllamaApi {
    param([string]$BaseUrl)
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/tags" -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Ensure-OllamaInstalled {
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
        Write-Host "Ollama already installed."
        return
    }

    if ($SkipOllamaInstall) {
        throw "Ollama is not installed and -SkipOllamaInstall was set."
    }

    Write-Host "Ollama not found. Trying winget install..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    } else {
        $installer = Join-Path $env:TEMP "OllamaSetup.exe"
        Write-Host "Downloading Ollama installer..."
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installer
        Write-Host "Launching installer (complete the UI if prompted)..."
        Start-Process -FilePath $installer -Wait
    }

    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")

    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        throw "Ollama install finished, but 'ollama' is still not on PATH. Open a new terminal and re-run setup."
    }
}

function Ensure-OllamaRunning {
    param([string]$BaseUrl)

    if (Test-OllamaApi -BaseUrl $BaseUrl) {
        Write-Host "Ollama API is reachable at $BaseUrl"
        return
    }

    Write-Host "Starting 'ollama serve' in background..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 2
        if (Test-OllamaApi -BaseUrl $BaseUrl) {
            Write-Host "Ollama is ready."
            return
        }
    } while ((Get-Date) -lt $deadline)

    throw "Could not reach Ollama at $BaseUrl. Run 'ollama serve' manually and retry."
}

Write-Host "IA Agent Developer setup" -ForegroundColor Green
Write-Host "Root: $Root"
Write-Host "Model: $Model"
Write-Host "Ollama: $OllamaHost"

Write-Step "Checking Python"
$Python = Get-PythonCommand
Write-Host "Using: $Python"
& $Python --version

Write-Step "Installing Python project dependencies"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]"

Write-Step "Ensuring Ollama"
Ensure-OllamaInstalled
Ensure-OllamaRunning -BaseUrl $OllamaHost

if (-not $SkipModelPull) {
    Write-Step "Pulling model '$Model'"
    ollama pull $Model
} else {
    Write-Host "Skipping model pull."
}

Write-Step "Creating workspace '$Workspace'"
New-Item -ItemType Directory -Force -Path (Join-Path $Root $Workspace) | Out-Null

$env:OLLAMA_HOST = $OllamaHost
$env:OLLAMA_MODEL = $Model

if (-not $SkipTests) {
    Write-Step "Running unit tests"
    & $Python -m pytest -q
}

if (-not $SkipSmoke) {
    Write-Step "Running dry-run smoke test"
    & $Python .\ollama_agent.py `
        --workspace $Workspace `
        --model $Model `
        --dry-run `
        --verbose `
        "Create a file called demo.txt with the content hello"
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next commands:" -ForegroundColor Yellow
Write-Host "  python ollama_agent.py --workspace .\$Workspace --model $Model --verbose `"Create a file called demo.txt with the content hello`""
Write-Host "  python ollama_agent.py --workspace .\$Workspace --model $Model `"Create a python starter project called demo_py in folder demo_py`""
Write-Host "  python verify_agent.py --verbose"
