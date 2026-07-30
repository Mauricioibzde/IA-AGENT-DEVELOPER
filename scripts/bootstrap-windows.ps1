#Requires -Version 5.1
<#
.SYNOPSIS
  Clone/update the Forge branch on Windows and start the local platform.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1 -CloneIfMissing

.EXAMPLE
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

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ""
    Write-Host ("==> " + $Message) -ForegroundColor Cyan
}

function Assert-Command {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Hint
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw ("Command not found: " + $Name + ". " + $Hint)
    }
}

Write-Host "Forge - bootstrap Windows (local)" -ForegroundColor Green
Write-Host ("Branch: " + $Branch)
Write-Host ("Folder: " + $TargetDir)

Assert-Command -Name "git" -Hint "Install Git: https://git-scm.com/download/win"
Assert-Command -Name "python" -Hint "Install Python 3.11+ with Add to PATH: https://www.python.org/downloads/"
Assert-Command -Name "node" -Hint "Install Node.js 18+: https://nodejs.org/"
Assert-Command -Name "npm" -Hint "Install Node.js 18+ (includes npm)."

$inRepo = Test-Path (Join-Path (Get-Location) "ia_platform\server.py")
if ($inRepo) {
    $Root = (Resolve-Path ".").Path
    Write-Host ("Using current repo: " + $Root)
}
elseif (Test-Path (Join-Path $TargetDir "ia_platform\server.py")) {
    $Root = (Resolve-Path $TargetDir).Path
    Set-Location $Root
    Write-Host ("Using existing repo: " + $Root)
}
elseif ($CloneIfMissing) {
    Write-Step -Message "Cloning repository"
    $parent = Split-Path -Parent $TargetDir
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    if (Test-Path $TargetDir) {
        throw ("Folder already exists but is not the repo: " + $TargetDir)
    }
    git clone --branch $Branch --single-branch $RepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    $Root = (Resolve-Path $TargetDir).Path
    Set-Location $Root
}
else {
    $msg = @(
        "Repository not found.",
        "",
        "Option A - automatic clone:",
        "  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1 -CloneIfMissing",
        "",
        "Option B - manual clone:",
        ("  git clone -b " + $Branch + " " + $RepoUrl + " `"$TargetDir`""),
        ("  cd `"$TargetDir`""),
        "  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1"
    ) -join [Environment]::NewLine
    throw $msg
}

Write-Step -Message ("Updating branch " + $Branch)
git fetch origin $Branch
if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
git checkout $Branch
if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
git pull origin $Branch
if ($LASTEXITCODE -ne 0) { throw "git pull failed" }

Write-Step -Message "Setup Python / Ollama"
& (Join-Path $Root "scripts\setup.ps1") -Model $Model -SkipSmoke -SkipTests

Write-Step -Message "Visual Engine Node dependencies"
Push-Location (Join-Path $Root "visual_engine")
try {
    npm install --omit=dev
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
}
finally {
    Pop-Location
}

if (-not $SkipVisionPull) {
    Write-Step -Message ("Pulling vision model " + $VisionModel + " (optional, may take a while)")
    try {
        ollama pull $VisionModel
    }
    catch {
        Write-Host ("Warning: could not pull " + $VisionModel + ". Continuing without vision.") -ForegroundColor Yellow
    }
}

if ($NoStart) {
    Write-Host ""
    Write-Host "Bootstrap done. To start:" -ForegroundColor Green
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run-platform.ps1"
    Write-Host "Then open: http://127.0.0.1:8787"
    exit 0
}

Write-Step -Message "Starting Forge at http://127.0.0.1:8787"
Write-Host "Keep this terminal open. Stop with Ctrl+C." -ForegroundColor Yellow
& (Join-Path $Root "scripts\run-platform.ps1")
