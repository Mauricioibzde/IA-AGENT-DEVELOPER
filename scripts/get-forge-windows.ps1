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
$RawBootstrap = "https://raw.githubusercontent.com/Mauricioibzde/IA-AGENT-DEVELOPER/$Branch/scripts/bootstrap-windows.ps1"
$TargetDir = Join-Path $HOME "IA-AGENT-DEVELOPER"

Write-Host ("Downloading Forge to " + $TargetDir + " (branch " + $Branch + ")...") -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git not found. Install: https://git-scm.com/download/win"
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
    # Critical: sync BEFORE running local scripts. An older clone may have a
    # broken bootstrap-windows.ps1 that fails to parse on Windows PowerShell 5.1.
    Write-Host "Repository already exists - syncing branch first..." -ForegroundColor Yellow
    Set-Location $TargetDir
    git fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
    git checkout $Branch
    if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
    git reset --hard ("origin/" + $Branch)
    if ($LASTEXITCODE -ne 0) { throw "git reset failed" }
}

Set-Location $TargetDir

$bootstrapLocal = Join-Path $TargetDir "scripts\bootstrap-windows.ps1"
if (-not (Test-Path $bootstrapLocal)) {
    throw ("bootstrap not found after sync: " + $bootstrapLocal)
}

# Prefer a fresh copy from GitHub so a stale/corrupt local file cannot block install.
$bootstrapTemp = Join-Path $env:TEMP ("forge-bootstrap-windows-" + $Branch.Replace("/", "-") + ".ps1")
try {
    Write-Host "Fetching latest bootstrap script..."
    Invoke-WebRequest -Uri $RawBootstrap -OutFile $bootstrapTemp -UseBasicParsing
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bootstrapTemp -TargetDir $TargetDir -Branch $Branch
}
catch {
    Write-Host ("Fresh bootstrap download failed (" + $_.Exception.Message + "). Falling back to local script...") -ForegroundColor Yellow
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bootstrapLocal -TargetDir $TargetDir -Branch $Branch
}
