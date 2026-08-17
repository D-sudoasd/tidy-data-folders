<#
.SYNOPSIS
  Map-first inventory of a folder tree (depth-2 + extension histogram + document signals).
.PARAMETER Root
  Project root to inventory.
.PARAMETER Json
  Emit JSON instead of markdown-ish text.
.PARAMETER MaxDepthList
  How deep to list directory names (default 2).
.NOTES
  Profile and competing-background scoring live in survey_signals.py. This
  script forwards to that module so PowerShell callers stay in sync with
  `python scripts/tidy.py survey`.
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [switch]$Json,
  [int]$MaxDepthList = 2
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Root)) { throw "Root not found: $Root" }

$signalScript = Join-Path $PSScriptRoot 'survey_signals.py'
if (-not (Test-Path -LiteralPath $signalScript)) {
  throw "survey_signals.py is missing next to inventory.ps1: $signalScript"
}

$launcher = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
  $launcher = @('python')
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
  $launcher = @('py', '-3')
}
elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
  $launcher = @('python3')
}
else {
  throw "Python was not found. Survey signals live in survey_signals.py; install Python 3.10+ or run ``python scripts/tidy.py survey``."
}

$command = $launcher[0]
$prefix = @()
if ($launcher.Count -gt 1) {
  $prefix = $launcher[1..($launcher.Count - 1)]
}
$argList = @($signalScript, '--root', $Root, '--max-depth', [string]$MaxDepthList)
if ($Json) { $argList += '--json' }

& $command @($prefix + $argList)
exit $LASTEXITCODE
