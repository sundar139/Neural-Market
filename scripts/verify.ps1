#Requires -Version 5.1
<#
.SYNOPSIS
    Run the full NeuralMarket quality gate using the project-local interpreter.
.DESCRIPTION
    Runs Ruff lint, Ruff format check, mypy, pytest with branch coverage,
    pre-commit on all files, a CLI help smoke test, and environment-report
    generation. Stops on the first failure. Does not change the permanent
    PowerShell execution policy.
#>
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-LastExitCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    if ($LASTEXITCODE -ne 0) {
        throw "Verification failed: $CommandName exited with code $LASTEXITCODE."
    }
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

& $Py -m ruff check .
Assert-LastExitCode "ruff check"
& $Py -m ruff format --check .
Assert-LastExitCode "ruff format --check"
& $Py -m mypy src
Assert-LastExitCode "mypy"
& $Py -m pytest -m "unit or integration" --cov=neuralmarket --cov-branch --cov-report=term-missing --cov-fail-under=85
Assert-LastExitCode "pytest"
& $Py -m pre_commit run --all-files
Assert-LastExitCode "pre-commit"
& $Py -m neuralmarket --help
Assert-LastExitCode "neuralmarket --help"
& $Py -m neuralmarket data pilot --help
Assert-LastExitCode "neuralmarket data pilot --help"
& $Py -m neuralmarket data pilot prepare --help
Assert-LastExitCode "neuralmarket data pilot prepare --help"
& $Py -m neuralmarket environment check --config "configs/reproducibility/default.yaml" --output "reports/environment/environment_check.json"
Assert-LastExitCode "neuralmarket environment check"
& $Py -m neuralmarket data contracts validate
Assert-LastExitCode "neuralmarket data contracts validate"
& $Py -m neuralmarket data manifests verify --source "data/manifests/source_manifest_v1.json" --split "data/manifests/split_manifest_v1.json"
Assert-LastExitCode "neuralmarket data manifests verify"

Write-Host "Verification complete."
