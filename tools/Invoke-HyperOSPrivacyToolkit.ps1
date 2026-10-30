[CmdletBinding()]
param(
    [ValidateSet('doctor', 'list-actions', 'analyze', 'apply', 'restore', 'sample-filemanager-ads')]
    [string]$Command = 'analyze',
    [string]$Action,
    [string]$AdbPath,
    [string]$Serial,
    [string]$Log,
    [switch]$Confirm,
    [switch]$AcknowledgeDataDeletion,
    [switch]$IncludeExperimental,
    [int]$Attempts = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Get-Command python, py -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $python) { throw 'Python 3.11 or newer was not found in PATH.' }

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $arguments = @('-m', 'hyperos_privacy_toolkit')
    if ($AdbPath) { $arguments += @('--adb', $AdbPath) }
    if ($Serial) { $arguments += @('--serial', $Serial) }
    $arguments += $Command

    switch ($Command) {
        'analyze' {
            if ($Action) { $arguments += @('--action', $Action) }
            if ($IncludeExperimental) { $arguments += '--include-experimental' }
        }
        'apply' {
            if (-not $Action) { throw '-Action is required for apply.' }
            if (-not $Confirm) { throw '-Confirm is required for apply.' }
            $arguments += @($Action, '--confirm', $Action)
            if ($AcknowledgeDataDeletion) { $arguments += '--acknowledge-data-deletion' }
            if ($IncludeExperimental) { $arguments += '--include-experimental' }
        }
        'restore' {
            if (-not $Action -or -not $Log) { throw '-Action and -Log are required for restore.' }
            if (-not $Confirm) { throw '-Confirm is required for restore.' }
            $arguments += @($Log, '--action', $Action, '--confirm', $Action)
            if ($IncludeExperimental) { $arguments += '--include-experimental' }
        }
        'sample-filemanager-ads' {
            $arguments += @('--attempts', [string]$Attempts, '--include-experimental')
        }
    }

    & $python.Source @arguments
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}
