param(
    [Parameter(Mandatory=$true)][string]$Id,
    [Parameter(Mandatory=$true)][string]$Objective,
    [Parameter(Mandatory=$true)]
    [ValidateSet("R0","R1","R2","R3","R4","R5")]
    [string]$Risk,
    [string[]]$Invariant = @(),
    [string[]]$StopCondition = @(),
    [string[]]$ExpectedFile = @(),
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
$python = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

$argsList = @(
    "tools\agent_task.py", "start",
    "--id", $Id,
    "--objective", $Objective,
    "--risk", $Risk
)

foreach ($x in $Invariant)     { $argsList += @("--invariant", $x) }
foreach ($x in $StopCondition){ $argsList += @("--stop-condition", $x) }
foreach ($x in $ExpectedFile) { $argsList += @("--expected-file", $x) }
if ($AllowDirty)              { $argsList += "--allow-dirty" }

& $python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
