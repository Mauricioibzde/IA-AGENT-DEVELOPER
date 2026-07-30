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

Write-Host ("Downloading Forge to " + $TargetDir + " (branch " + $Branch + ")...") -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git not found. Install: https://git-scm.com/download/win"
}

if (-not (Test-Path (Join-Path $TargetDir "ia_platform\server.py"))) {
    if (Test-Path $TargetDir) {
        throw ("Folder exists but is not the repository: " + $TargetDir)
    }
    git clone --branch $Branch --single-branch $RepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
}
else {
    Write-Host "Repository already exists - updating..."
}

Set-Location $TargetDir
& (Join-Path $TargetDir "scripts\bootstrap-windows.ps1")
