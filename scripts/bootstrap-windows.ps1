#Requires -Version 5.1
<#
.SYNOPSIS
  Update Forge on Windows, install Python/Node deps if needed, and start locally.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1
#>

[CmdletBinding()]
param(
    [string]$RepoUrl = "https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git",
    [string]$Branch = "cursor/windows-python-bootstrap-40ee",
    [string]$TargetDir = (Join-Path $HOME "IA-AGENT-DEVELOPER"),
    [string]$Model = "deepseek-coder:6.7b",
    [switch]$CloneIfMissing,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ""
    Write-Host ("==> " + $Message) -ForegroundColor Cyan
}

function Refresh-ProcessPath {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($machine -and $user) { $env:Path = $machine + ";" + $user }
    elseif ($machine) { $env:Path = $machine }
    elseif ($user) { $env:Path = $user }
}

function Ensure-CommandOrWinget {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WingetId,
        [Parameter(Mandatory = $true)][string]$Hint
    )
    if (Get-Command $Name -ErrorAction SilentlyContinue) { return }
    Write-Host ($Name + " not found. Trying winget " + $WingetId + "...") -ForegroundColor Yellow
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw ($Name + " not found. " + $Hint)
    }
    winget install -e --id $WingetId --accept-package-agreements --accept-source-agreements
    Refresh-ProcessPath
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw ($Name + " installed but not on PATH yet. Open a NEW PowerShell and re-run bootstrap. Hint: " + $Hint)
    }
}

Write-Host "Forge - bootstrap Windows (local)" -ForegroundColor Green
Write-Host ("Branch: " + $Branch)
Write-Host ("Folder: " + $TargetDir)

Ensure-CommandOrWinget -Name "git" -WingetId "Git.Git" -Hint "Install Git: https://git-scm.com/download/win"
Ensure-CommandOrWinget -Name "node" -WingetId "OpenJS.NodeJS.LTS" -Hint "Install Node.js 18+: https://nodejs.org/"
Ensure-CommandOrWinget -Name "npm" -WingetId "OpenJS.NodeJS.LTS" -Hint "Install Node.js 18+ (includes npm)."

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
    throw ("Repository not found at " + $TargetDir + ". Re-run with -CloneIfMissing or cd into the repo first.")
}

Write-Step -Message ("Updating branch " + $Branch)
# Works even for --single-branch clones that do not track other remotes yet.
git remote set-branches --add origin $Branch 2>$null
git fetch origin $Branch
if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
git checkout -B $Branch FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
git reset --hard FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "git reset failed" }
git branch --set-upstream-to=("origin/" + $Branch) $Branch 2>$null
git pull origin $Branch 2>$null

Write-Step -Message "Setup Python / Ollama"
& (Join-Path $Root "scripts\setup.ps1") -Model $Model -SkipSmoke -SkipTests

Write-Step -Message "Visual Engine Node dependencies"
$ve = Join-Path $Root "visual_engine"
if (Test-Path (Join-Path $ve "package.json")) {
    Push-Location $ve
    try {
        npm install --omit=dev
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    }
    finally {
        Pop-Location
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
