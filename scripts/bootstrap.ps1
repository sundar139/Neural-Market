#Requires -Version 5.1
<#
.SYNOPSIS
    Create the project-local .venv and install NeuralMarket in editable dev mode.
.DESCRIPTION
    Resolves the repository root relative to this script, verifies Python 3.11,
    creates .venv if absent, installs build tooling and the package with dev
    dependencies, and installs pre-commit hooks. Stops on the first failed
    command. Never modifies global Python or Git configuration.
#>
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-LastExitCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap failed: $CommandName exited with code $LASTEXITCODE."
    }
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating .venv with Python 3.11..."
    & py -3.11 --version
    Assert-LastExitCode "Python 3.11 discovery"
    & py -3.11 -m venv (Join-Path $RepoRoot ".venv")
    Assert-LastExitCode "virtual environment creation"
}

& $VenvPython --version
Assert-LastExitCode "project Python version"
$version = & $VenvPython -c "import sys; print('%d.%d' % sys.version_info[:2])"
Assert-LastExitCode "project Python version check"
if ($version -ne "3.11") {
    throw "Project interpreter is Python $version, expected 3.11."
}

& $VenvPython -m pip install --upgrade pip setuptools wheel
Assert-LastExitCode "build tooling installation"
& $VenvPython -m pip install -e ".[dev,data]"
Assert-LastExitCode "project dependency installation"
& (Join-Path $RepoRoot ".venv\Scripts\pre-commit.exe") install
Assert-LastExitCode "pre-commit hook installation"

Write-Host "Bootstrap complete."
