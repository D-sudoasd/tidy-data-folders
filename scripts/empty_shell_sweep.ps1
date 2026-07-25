<#
.SYNOPSIS
  Remove empty shell directories left by applied moves — not all empty dirs under Root.
.PARAMETER Root
  Project root.
.PARAMETER PlanCsv
  Move plan; only approved executable rows (or AppliedLog preferred).
.PARAMETER AppliedLog
  MOVE_LOG with status=applied — preferred input (parents of src).
.PARAMETER Preserve
  Directory names never removed.
.PARAMETER WhatIf
  Report only; simulates cascading removes in memory.
.PARAMETER MoveLog
  Unified 12-col log path.
.PARAMETER Aggressive
  MAINTENANCE: full-tree empty sweep (requires explicit confirm string).
.PARAMETER AggressiveConfirm
  Must be 'I_UNDERSTAND_FULL_TREE_SWEEP' with -Aggressive.
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [string]$PlanCsv = '',
  [string]$AppliedLog = '',
  [string[]]$Preserve = @('to_sort', '00_docs', 'docs', '01_papers', '02_other_docs', '03_figures_exports', '99_archive'),
  [switch]$WhatIf,
  [string]$MoveLog = '',
  [switch]$Aggressive,
  [string]$AggressiveConfirm = ''
)

$ErrorActionPreference = 'Stop'
$LogFields = @(
  'run_id', 'plan_id', 'row_id', 'timestamp_utc', 'src', 'dst', 'kind',
  'status', 'reason', 'error', 'sha256_before', 'sha256_after'
)

if (-not (Test-Path -LiteralPath $Root)) { throw "Root not found: $Root" }
$Root = (Resolve-Path -LiteralPath $Root).Path
$ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$runId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '_sweep'
$candidates = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$would = [System.Collections.Generic.List[string]]::new()
$removed = [System.Collections.Generic.List[string]]::new()
$errors = [System.Collections.Generic.List[string]]::new()
# In-memory set of dirs removed during WhatIf cascade
$virtRemoved = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

function Test-UnderRoot([string]$Full, [string]$RootPath) {
  $fullN = [System.IO.Path]::GetFullPath($Full)
  $rootN = [System.IO.Path]::GetFullPath($RootPath).TrimEnd('\') + '\'
  return $fullN.StartsWith($rootN, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-IsReparse([string]$Path) {
  $i = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  return [bool]($i.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Assert-NoReparseInChain([string]$Full, [string]$RootPath) {
  $rootN = [System.IO.Path]::GetFullPath($RootPath).TrimEnd('\')
  $fullN = [System.IO.Path]::GetFullPath($Full)
  if (-not $fullN.StartsWith($rootN, [StringComparison]::OrdinalIgnoreCase)) {
    throw "path not under root: $Full"
  }
  $rel = $fullN.Substring($rootN.Length).TrimStart('\')
  if ([string]::IsNullOrWhiteSpace($rel)) { return }
  $cur = $rootN
  foreach ($seg in ($rel -split '[\\/]', [System.StringSplitOptions]::RemoveEmptyEntries)) {
    $cur = Join-Path $cur $seg
    if (Test-Path -LiteralPath $cur) {
      if (Test-IsReparse -Path $cur) { throw "reparse in chain: $cur" }
    }
  }
}

function Add-ParentChain([string]$FileOrDir) {
  if (-not $FileOrDir) { return }
  $p = Split-Path -Parent $FileOrDir
  while ($p -and (Test-UnderRoot $p $Root) -and ($p.TrimEnd('\') -ne $Root.TrimEnd('\'))) {
    try { Assert-NoReparseInChain -Full $p -RootPath $Root } catch { $errors.Add($_.Exception.Message); return }
    [void]$candidates.Add($p)
    $p = Split-Path -Parent $p
  }
}

function Test-IsApproved($Row) {
  $a = [string]$Row.approved
  return @('true', 'yes', '1', 'y') -contains $a.ToLowerInvariant()
}

function Write-LogRow([string]$Path, [hashtable]$Map) {
  if (-not $Path) { return }
  $parent = Split-Path -Parent $Path
  if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }
  if (-not (Test-Path -LiteralPath $Path)) {
    ($LogFields -join ',') | Set-Content -LiteralPath $Path -Encoding utf8
  } else {
    $first = Get-Content -LiteralPath $Path -TotalCount 1 -Encoding utf8
    $expected = $LogFields -join ','
    if ($first.Trim() -ne $expected) {
      throw "MOVE_LOG header mismatch: $first"
    }
  }
  $vals = foreach ($k in $LogFields) {
    $v = [string]$Map[$k]
    if ($v.Length -gt 0 -and @('=', '+', '-', '@') -contains $v[0]) { $v = "'" + $v }
    if ($v.Contains('"') -or $v.Contains(',')) { '"' + ($v -replace '"', '""') + '"' } else { $v }
  }
  Add-Content -LiteralPath $Path -Value ($vals -join ',') -Encoding utf8
}

if ($Aggressive) {
  if ($AggressiveConfirm -ne 'I_UNDERSTAND_FULL_TREE_SWEEP') {
    Write-Output "ERROR: -Aggressive requires -AggressiveConfirm I_UNDERSTAND_FULL_TREE_SWEEP"
    exit 2
  }
  Get-ChildItem -LiteralPath $Root -Recurse -Directory -Force -ErrorAction Stop | ForEach-Object {
    try {
      Assert-NoReparseInChain -Full $_.FullName -RootPath $Root
      [void]$candidates.Add($_.FullName)
    } catch { $errors.Add($_.Exception.Message) }
  }
} elseif ($AppliedLog) {
  if (-not (Test-Path -LiteralPath $AppliedLog)) {
    Write-Output "ERROR: AppliedLog not found: $AppliedLog"
    exit 2
  }
  Import-Csv -LiteralPath $AppliedLog | ForEach-Object {
    if ([string]$_.status -ne 'applied') { return }
    $src = [string]$_.src
    if ([string]::IsNullOrWhiteSpace($src) -or $src -like '(removed*') { return }
    if ($src.Contains('..')) { $errors.Add("skip src with ..: $src"); return }
    if ([System.IO.Path]::IsPathRooted($src)) { $errors.Add("skip absolute src: $src"); return }
    $full = [System.IO.Path]::GetFullPath((Join-Path $Root $src))
    if (Test-UnderRoot $full $Root) { Add-ParentChain $full }
  }
} elseif ($PlanCsv) {
  if (-not (Test-Path -LiteralPath $PlanCsv)) {
    Write-Output "ERROR: PlanCsv not found: $PlanCsv"
    exit 2
  }
  Import-Csv -LiteralPath $PlanCsv | ForEach-Object {
    if (-not (Test-IsApproved $_)) { return }
    $kind = if ($_.action) { [string]$_.action } elseif ($_.kind) { [string]$_.kind } else { 'move' }
    if (@('move', 'rename_parent', 'archive', 'doc_rename', 'rename', 'normalize', 'move_only') -notcontains $kind.ToLowerInvariant()) {
      return
    }
    $src = [string]$_.src
    if ([string]::IsNullOrWhiteSpace($src)) { return }
    if ($src.Contains('..') -or [System.IO.Path]::IsPathRooted($src)) {
      $errors.Add("skip bad src: $src"); return
    }
    $full = [System.IO.Path]::GetFullPath((Join-Path $Root $src))
    if (Test-UnderRoot $full $Root) { Add-ParentChain $full }
  }
} else {
  Write-Output "ERROR: pass -AppliedLog or -PlanCsv (or -Aggressive with confirm)"
  Write-Output "empty_shell_count: 0"
  exit 2
}

$preserveSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($x in $Preserve) { [void]$preserveSet.Add($x) }

$ordered = $candidates | Sort-Object { $_.Length } -Descending

function Test-VirtuallyEmpty([string]$Dir) {
  if ($virtRemoved.Contains($Dir)) { return $true }
  if (-not (Test-Path -LiteralPath $Dir)) { return $true }
  try {
    $kids = @(Get-ChildItem -LiteralPath $Dir -Force -ErrorAction Stop)
  } catch {
    $errors.Add("enum failed: $Dir :: $($_.Exception.Message)")
    return $false
  }
  foreach ($k in $kids) {
    if ($k.PSIsContainer) {
      if (-not $virtRemoved.Contains($k.FullName)) { return $false }
    } else {
      return $false
    }
  }
  return $true
}

foreach ($dir in $ordered) {
  if (-not (Test-Path -LiteralPath $dir)) { continue }
  if (-not (Test-UnderRoot $dir $Root)) { continue }
  if ($dir.TrimEnd('\') -eq $Root.TrimEnd('\')) { continue }
  $leaf = Split-Path -Leaf $dir
  $rel = $dir.Substring($Root.Length).TrimStart('\')
  if ($preserveSet.Contains($leaf) -or $preserveSet.Contains($rel.Replace('\', '/'))) {
    continue
  }
  try {
    if (Test-IsReparse $dir) {
      $errors.Add("skip reparse: $rel")
      continue
    }
    Assert-NoReparseInChain -Full $dir -RootPath $Root
  } catch {
    $errors.Add("skip reparse chain: $rel :: $($_.Exception.Message)")
    continue
  }

  $empty = if ($WhatIf) { Test-VirtuallyEmpty $dir } else {
    try {
      (@(Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop)).Count -eq 0
    } catch {
      $errors.Add("enum failed: $rel :: $($_.Exception.Message)")
      $false
    }
  }
  if (-not $empty) { continue }

  if ($WhatIf) {
    Write-Output "WHATIF remove empty: $rel"
    $would.Add($rel)
    [void]$virtRemoved.Add($dir)
    continue
  }
  try {
    Remove-Item -LiteralPath $dir -Force -ErrorAction Stop
    $removed.Add($rel)
    if ($MoveLog) {
      Write-LogRow -Path $MoveLog -Map @{
        run_id        = $runId
        plan_id       = ''
        row_id        = ''
        timestamp_utc = $ts
        src           = $rel
        dst           = '(removed empty shell)'
        kind          = 'shell_remove'
        status        = 'applied'
        reason        = 'empty shell after planned move'
        error         = ''
        sha256_before = ''
        sha256_after  = ''
      }
    }
    Write-Output "removed empty: $rel"
  } catch {
    $errors.Add("remove failed: $rel :: $($_.Exception.Message)")
  }
}

Write-Output "empty_shell_count: $($removed.Count)"
Write-Output "would_remove_count: $($would.Count)"
if ($errors.Count -gt 0) {
  Write-Output "errors: $($errors.Count)"
  $errors | ForEach-Object { Write-Output "ERROR: $_" }
  exit 1
}
exit 0
