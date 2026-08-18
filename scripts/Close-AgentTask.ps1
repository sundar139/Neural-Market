param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(
        "IMPLEMENTED",
        "VALIDATED",
        "BLOCKED",
        "NEEDS_DECISION",
        "NEEDS_EXTERNAL_ACTION",
        "SCIENTIFICALLY_INCONCLUSIVE"
    )]
    [string]$Outcome,

    [Parameter(Mandatory=$true)][string]$Summary,
    [string]$NextAction
)

$ErrorActionPreference = "Stop"
$python = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

$argsList = @(
    "tools\agent_task.py", "finish",
    "--outcome", $Outcome,
    "--summary", $Summary
)

if ($NextAction) { $argsList += @("--next-action", $NextAction) }

& $python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
