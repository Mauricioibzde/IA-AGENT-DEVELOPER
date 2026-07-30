#Requires -Version 5.1
<#
.SYNOPSIS
  One-liner: sync Forge on Windows, install missing tools, and start locally.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/Mauricioibzde/IA-AGENT-DEVELOPER/main/scripts/get-forge-windows.ps1 | iex"
#>

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/Mauricioibzde/IA-AGENT-DEVELOPER.git"
# Use this branch until the Windows Python bootstrap PR is merged into main.
$Branch = "cursor/windows-python-bootstrap-40ee"
$RawBootstrap = "https://raw.githubusercontent.com/Mauricioibzde/IA-AGENT-DEVELOPER/$Branch/scripts/bootstrap-windows.ps1"
$TargetDir = Join-Path $HOME "IA-AGENT-DEVELOPER"

Write-Host ("Forge local Windows -> " + $TargetDir + " (branch " + $Branch + ")") -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Installing Git with winget..."
        winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git not found. Install: https://git-scm.com/download/win then open a NEW PowerShell."
    }
}

$repoReady = Test-Path (Join-Path $TargetDir "ia_platform\server.py")
if (-not $repoReady) {
    if (Test-Path $TargetDir) {
        throw ("Folder exists but is not the repository: " + $TargetDir)
    }
    git clone --branch $Branch --single-branch $RepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
}
else {
    # Works even for --single-branch clones that do not track other remotes yet.
    Write-Host "Repository already exists - syncing branch first..." -ForegroundColor Yellow
    Set-Location $TargetDir
    git remote set-branches --add origin $Branch 2>$null
    git fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
    git checkout -B $Branch FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
    git reset --hard FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw "git reset failed" }
}

Set-Location $TargetDir

$bootstrapTemp = Join-Path $env:TEMP ("forge-bootstrap-windows-" + $Branch.Replace("/", "-") + ".ps1")
Write-Host "Fetching latest bootstrap script..."
Invoke-WebRequest -Uri $RawBootstrap -OutFile $bootstrapTemp -UseBasicParsing
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bootstrapTemp -TargetDir $TargetDir -Branch $Branch
