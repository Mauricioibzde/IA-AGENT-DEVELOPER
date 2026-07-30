#Requires -Version 5.1
<#
.SYNOPSIS
  Shared Windows Python discovery / install helpers for Forge scripts.
#>

function Test-PythonExecutable {
    param([Parameter(Mandatory = $true)][string]$ExePath)
    if (-not (Test-Path -LiteralPath $ExePath)) { return $false }
    # Ignore Windows Store alias stubs that open the Store instead of Python.
    if ($ExePath -match '\\WindowsApps\\Python(?:\.exe|3\.exe)$') { return $false }
    try {
        $versionText = & $ExePath --version 2>&1 | Out-String
        if ($versionText -match "Python\s+(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            return ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10))
        }
    } catch {
        return $false
    }
    return $false
}

function Get-PythonCommand {
    $candidates = New-Object System.Collections.Generic.List[string]

    foreach ($name in @("python", "python3", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) { [void]$candidates.Add($cmd.Source) }
    }

    # py launcher can target a specific runtime even when "python" is a Store stub.
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        foreach ($arg in @("-3.12", "-3.11", "-3.10", "-3")) {
            try {
                $resolved = & py $arg -c "import sys; print(sys.executable)" 2>$null
                if ($resolved) { [void]$candidates.Add($resolved.ToString().Trim()) }
            } catch { }
        }
    }

    $localAppData = $env:LOCALAPPDATA
    $programFiles = ${env:ProgramFiles}
    $programFilesX86 = ${env:ProgramFiles(x86)}
    $userProfile = $env:USERPROFILE
    foreach ($base in @($localAppData, $programFiles, $programFilesX86, $userProfile)) {
        if (-not $base) { continue }
        foreach ($pattern in @(
            (Join-Path $base "Programs\Python\Python3*\python.exe"),
            (Join-Path $base "Python\Python3*\python.exe"),
            (Join-Path $base "AppData\Local\Programs\Python\Python3*\python.exe")
        )) {
            Get-Item $pattern -ErrorAction SilentlyContinue | ForEach-Object {
                [void]$candidates.Add($_.FullName)
            }
        }
    }

    $seen = @{}
    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        $key = $candidate.ToLowerInvariant()
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = $true
        if (Test-PythonExecutable -ExePath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Refresh-ProcessPath {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($machine -and $user) {
        $env:Path = $machine + ";" + $user
    } elseif ($machine) {
        $env:Path = $machine
    } elseif ($user) {
        $env:Path = $user
    }
}

function Ensure-PythonInstalled {
    param([switch]$AutoInstall)

    $python = Get-PythonCommand
    if ($python) { return $python }

    if (-not $AutoInstall) {
        throw "Python 3.10+ not found. Install from https://www.python.org/downloads/ (check Add python.exe to PATH) and re-run setup."
    }

    Write-Host "Python 3.10+ not found. Installing with winget..." -ForegroundColor Yellow
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget not found. Install Python 3.12 from https://www.python.org/downloads/ (check Add python.exe to PATH), open a NEW PowerShell, and re-run setup."
    }

    # Out-Host keeps winget logs off the function return pipeline (critical in Windows PowerShell).
    & winget.exe install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements | Out-Host
    Refresh-ProcessPath
    Start-Sleep -Seconds 2
    Refresh-ProcessPath

    $python = Get-PythonCommand
    if (-not $python) {
        # winget just installed; probe the usual path even if PATH is stale in this shell.
        foreach ($guess in @(
            (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
            (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
            (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe")
        )) {
            if (Test-PythonExecutable -ExePath $guess) {
                $python = $guess
                break
            }
        }
    }
    if (-not $python) {
        throw "Python was installed but is not visible yet. Close this terminal, open a NEW PowerShell, cd to the repo, and re-run setup."
    }
    return $python
}
