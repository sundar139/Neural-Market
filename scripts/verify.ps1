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

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

& $Py -m ruff check .
& $Py -m ruff format --check .
& $Py -m mypy src
& $Py -m pytest -m "unit or integration" --cov=neuralmarket --cov-branch --cov-report=term-missing --cov-fail-under=85
& $Py -m pre_commit run --all-files
& $Py -m neuralmarket --help
& $Py -m neuralmarket environment check --config "configs/reproducibility/default.yaml" --output "reports/environment/environment_check.json"

Write-Host "Verification complete."
