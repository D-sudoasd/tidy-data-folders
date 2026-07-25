<#
.SYNOPSIS
  Apply unit moves from a plan CSV with root containment, reparse checks, and full preflight.
.PARAMETER PlanCsv
  CSV: src,dst + approved (required) + optional kind,action,reason,row_id,plan_id,src_size,src_sha256
.PARAMETER Root
  Project root (all src/dst must stay under Root; relative paths only).
.PARAMETER MoveLog
  Unified 12-column MOVE_LOG path.
.PARAMETER WhatIf
  Dry-run after preflight.
.PARAMETER UnsafeAllowUnapproved
  MAINTENANCE ONLY: process rows without approved=true (default OFF).
.PARAMETER RunId
  Optional run id (default UTC + random).
#>
param(
  [Parameter(Mandatory = $true)][string]$PlanCsv,
  [Parameter(Mandatory = $true)][string]$Root,
  [string]$MoveLog = '',
  [switch]$WhatIf,
  [switch]$UnsafeAllowUnapproved,
  [string]$RunId = ''
)

$ErrorActionPreference = 'Stop'
$AllowedKinds = @('move', 'rename_parent', 'archive', 'shell_remove', 'path_rewrite', 'doc_rename')
# Prefer action column; fall back to kind
$LogFields = @(
  'run_id', 'plan_id', 'row_id', 'timestamp_utc', 'src', 'dst', 'kind',
  'status', 'reason', 'error', 'sha256_before', 'sha256_after'
)

if (-not (Test-Path -LiteralPath $Root)) { throw "Root not found: $Root" }
if (-not (Test-Path -LiteralPath $PlanCsv)) { throw "PlanCsv not found: $PlanCsv" }
$Root = (Resolve-Path -LiteralPath $Root).Path
$ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$day = (Get-Date).ToString('yyyyMMdd')
if (-not $MoveLog) { $MoveLog = Join-Path $Root ("MOVE_LOG_{0}_apply.csv" -f $day) }
if (-not $RunId) {
  $RunId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '_' + ([guid]::NewGuid().ToString('N').Substring(0, 8))
}

function Test-UnderRoot {
  param([string]$Full, [string]$RootPath)
  $fullN = [System.IO.Path]::GetFullPath($Full)
  $rootN = [System.IO.Path]::GetFullPath($RootPath).TrimEnd('\') + '\'
  return $fullN.StartsWith($rootN, [System.StringComparison]::OrdinalIgnoreCase) -or
    ($fullN.TrimEnd('\') -eq $RootPath.TrimEnd('\'))
}

function Test-IsReparse {
  param([string]$Path)
  $i = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  return [bool]($i.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Assert-NoReparseInChain {
  param([string]$Full, [string]$RootPath)
  $rootN = [System.IO.Path]::GetFullPath($RootPath).TrimEnd('\')
  $fullN = [System.IO.Path]::GetFullPath($Full)
  # Walk from root toward Full component by component
  $rel = $fullN
  if ($rel.StartsWith($rootN, [StringComparison]::OrdinalIgnoreCase)) {
    $rel = $rel.Substring($rootN.Length).TrimStart('\')
  } else {
    throw "path not under root: $Full"
  }
  if ([string]::IsNullOrWhiteSpace($rel)) { return }
  $cur = $rootN
  foreach ($seg in ($rel -split '[\\/]', [System.StringSplitOptions]::RemoveEmptyEntries)) {
    $cur = Join-Path $cur $seg
    if (Test-Path -LiteralPath $cur) {
      if (Test-IsReparse -Path $cur) {
        throw "reparse/symlink not allowed: $cur"
      }
    }
  }
}

function Resolve-PlanPath {
  param([string]$P, [string]$RootPath)
  if ([string]::IsNullOrWhiteSpace($P)) { throw "empty path" }
  $P = $P.Trim()
  if ($P.Contains('..')) { throw "path contains .. : $P" }
  if ($P.StartsWith('\\') -or $P.StartsWith('//')) { throw "UNC not allowed: $P" }
  if ([System.IO.Path]::IsPathRooted($P)) { throw "absolute path not allowed: $P" }
  $full = [System.IO.Path]::GetFullPath((Join-Path $RootPath $P))
  if (-not (Test-UnderRoot -Full $full -RootPath $RootPath)) {
    throw "path escapes root: $P"
  }
  Assert-NoReparseInChain -Full $full -RootPath $RootPath
  return $full
}

function Test-IsApproved {
  param($Row)
  $a = [string]$Row.approved
  if ([string]::IsNullOrWhiteSpace($a)) { return $null } # missing
  $l = $a.ToLowerInvariant()
  if (@('true', 'yes', '1', 'y') -contains $l) { return $true }
  if (@('false', 'no', '0', 'n') -contains $l) { return $false }
  return $null # invalid
}

function Get-NearestExistingAncestor {
  param([string]$Path)
  $p = $Path
  while ($p) {
    if (Test-Path -LiteralPath $p) { return $p }
    $parent = Split-Path -Parent $p
    if (-not $parent -or $parent -eq $p) { return $p }
    $p = $parent
  }
  return $Path
}

function Test-IsUnderOrEqual {
  param([string]$Child, [string]$Parent)
  $c = [System.IO.Path]::GetFullPath($Child).TrimEnd('\')
  $p = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\')
  if ($c.Equals($p, [StringComparison]::OrdinalIgnoreCase)) { return $true }
  $p2 = $p + '\'
  return $c.StartsWith($p2, [StringComparison]::OrdinalIgnoreCase)
}

function Assert-LogHeader {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return }
  $first = Get-Content -LiteralPath $Path -TotalCount 1 -Encoding utf8 -ErrorAction Stop
  $expected = $LogFields -join ','
  if ($first.Trim() -ne $expected) {
    throw "MOVE_LOG header mismatch. Expected: $expected ; Got: $first"
  }
}

function Write-LogRow {
  param([string]$Path, [hashtable]$Map)
  $parent = Split-Path -Parent $Path
  if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }
  if (-not (Test-Path -LiteralPath $Path)) {
    ($LogFields -join ',') | Set-Content -LiteralPath $Path -Encoding utf8
  } else {
    Assert-LogHeader -Path $Path
  }
  $vals = foreach ($k in $LogFields) {
    $v = [string]$Map[$k]
    if ($v.Length -gt 0 -and @('=', '+', '-', '@') -contains $v[0]) { $v = "'" + $v }
    if ($v.Contains('"') -or $v.Contains(',') -or $v.Contains("`n")) {
      '"' + ($v -replace '"', '""') + '"'
    } else { $v }
  }
  Add-Content -LiteralPath $Path -Value ($vals -join ',') -Encoding utf8
}

function Test-LogWritable {
  param([string]$Path)
  $parent = Split-Path -Parent $Path
  if (-not $parent) { $parent = (Get-Location).Path }
  if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }
  $probe = Join-Path $parent ("._tidy_log_probe_{0}.tmp" -f [guid]::NewGuid().ToString('N'))
  try {
    'probe' | Set-Content -LiteralPath $probe -Encoding utf8
    Remove-Item -LiteralPath $probe -Force
  } catch {
    throw "move log directory not writable: $parent"
  }
  if (Test-Path -LiteralPath $Path) {
    Assert-LogHeader -Path $Path
  }
}

# --- load plan ---
$rows = @(Import-Csv -LiteralPath $PlanCsv)
if ($rows.Count -eq 0) {
  Write-Output "preflight_ok: 0 jobs (empty plan)"
  exit 0
}

# require approved column
$props = @($rows[0].PSObject.Properties.Name)
if ($props -notcontains 'approved' -and -not $UnsafeAllowUnapproved) {
  Write-Output "PREFLIGHT FAILED — zero files moved"
  Write-Output "ERROR: plan missing required 'approved' column (set approved=true per row)"
  exit 3
}
if ($props -notcontains 'src' -or $props -notcontains 'dst') {
  Write-Output "PREFLIGHT FAILED — zero files moved"
  Write-Output "ERROR: plan must have src and dst columns"
  exit 3
}

$jobs = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()
$seenSrc = @{}
$seenDst = @{}
$nApproved = 0
$nUnapproved = 0
$nInvalidAction = 0
$planId = ''

foreach ($r in $rows) {
  $rowId = if ($r.row_id) { [string]$r.row_id } else { '' }
  $ap = Test-IsApproved -Row $r
  if ($null -eq $ap -and -not $UnsafeAllowUnapproved) {
    if ([string]::IsNullOrWhiteSpace([string]$r.approved)) {
      $errors.Add("row ${rowId}: approved missing (must be true or false)")
    } else {
      $errors.Add("row ${rowId}: approved invalid value: $($r.approved)")
    }
    continue
  }
  if (-not $UnsafeAllowUnapproved) {
    if (-not $ap) { $nUnapproved++; continue }
  } else {
    if ($null -ne $ap -and -not $ap) { $nUnapproved++; continue }
  }
  $nApproved++

  $kind = if ($r.action) { [string]$r.action } elseif ($r.kind) { [string]$r.kind } else { 'move' }
  $kind = $kind.Trim().ToLowerInvariant()
  if ($AllowedKinds -notcontains $kind) {
    $nInvalidAction++
    $errors.Add("row ${rowId}: unknown action/kind '$kind' (allowed: $($AllowedKinds -join ','))")
    continue
  }

  $reason = if ($r.reason) { [string]$r.reason } else { 'unit move' }
  $thisPlanId = if ($r.plan_id) { [string]$r.plan_id } else { '' }
  if ($planId -and $thisPlanId -and $thisPlanId -ne $planId) {
    $errors.Add("row ${rowId}: plan_id mismatch within file")
    continue
  }
  if ($thisPlanId) { $planId = $thisPlanId }

  try {
    $src = Resolve-PlanPath -P ([string]$r.src) -RootPath $Root
    $dst = Resolve-PlanPath -P ([string]$r.dst) -RootPath $Root
  } catch {
    $errors.Add("row ${rowId}: $($_.Exception.Message)")
    continue
  }

  if (-not (Test-Path -LiteralPath $src)) {
    $errors.Add("row ${rowId}: missing src: $($r.src)")
    continue
  }

  # plan/log must not live inside a source tree being moved
  $planFull = (Resolve-Path -LiteralPath $PlanCsv).Path
  $logFull = if (Test-Path -LiteralPath $MoveLog) { (Resolve-Path -LiteralPath $MoveLog).Path } else { [System.IO.Path]::GetFullPath($MoveLog) }
  if ((Test-IsUnderOrEqual -Child $planFull -Parent $src) -or (Test-IsUnderOrEqual -Child $logFull -Parent $src)) {
    $errors.Add("row ${rowId}: plan or move-log is inside src tree")
    continue
  }

  # dst must not be inside src
  if (Test-IsUnderOrEqual -Child $dst -Parent $src) {
    $errors.Add("row ${rowId}: dst is inside src")
    continue
  }

  $sk = $src.ToLowerInvariant()
  $dk = $dst.ToLowerInvariant()
  if ($seenSrc.ContainsKey($sk)) { $errors.Add("row ${rowId}: duplicate src"); continue }
  if ($seenDst.ContainsKey($dk)) { $errors.Add("row ${rowId}: duplicate dst"); continue }
  $seenSrc[$sk] = $true
  $seenDst[$dk] = $true

  if ($src -eq $dst) { continue }
  if (Test-Path -LiteralPath $dst) {
    $errors.Add("row ${rowId}: dest exists: $($r.dst)")
    continue
  }

  # nearest existing ancestor of dst parent must be a writable directory
  $dstParent = Split-Path -Parent $dst
  $anc = Get-NearestExistingAncestor -Path $dstParent
  if (-not (Test-UnderRoot -Full $anc -RootPath $Root)) {
    $errors.Add("row ${rowId}: dst ancestor outside root")
    continue
  }
  if (-not (Test-Path -LiteralPath $anc -PathType Container)) {
    $errors.Add("row ${rowId}: dst parent ancestor is not a directory: $anc")
    continue
  }
  try {
    if (Test-IsReparse -Path $anc) {
      $errors.Add("row ${rowId}: dst ancestor is reparse: $anc")
      continue
    }
  } catch {
    $errors.Add("row ${rowId}: cannot inspect dst ancestor: $($_.Exception.Message)")
    continue
  }

  $jobs.Add([pscustomobject]@{
      row_id  = $rowId
      plan_id = $thisPlanId
      src     = $src
      dst     = $dst
      kind    = $kind
      reason  = $reason
      src_rel = [string]$r.src
      dst_rel = [string]$r.dst
    })
}

# source ancestor overlap among jobs
for ($i = 0; $i -lt $jobs.Count; $i++) {
  for ($j = $i + 1; $j -lt $jobs.Count; $j++) {
    $a = $jobs[$i].src
    $b = $jobs[$j].src
    if ((Test-IsUnderOrEqual -Child $a -Parent $b) -or (Test-IsUnderOrEqual -Child $b -Parent $a)) {
      $errors.Add("src trees overlap: $($jobs[$i].src_rel) and $($jobs[$j].src_rel)")
    }
  }
}

try {
  Test-LogWritable -Path $MoveLog
} catch {
  $errors.Add($_.Exception.Message)
}

Write-Output "approved_rows: $nApproved unapproved_skipped: $nUnapproved invalid_action: $nInvalidAction"

if ($errors.Count -gt 0) {
  Write-Output "PREFLIGHT FAILED — zero files moved"
  $errors | ForEach-Object { Write-Output "ERROR: $_" }
  exit 3
}

if ($jobs.Count -eq 0) {
  Write-Output "preflight_ok: 0 jobs"
  if ($nInvalidAction -gt 0) { exit 3 }
  exit 0
}

Write-Output "preflight_ok: $($jobs.Count) jobs run_id=$RunId"

$ok = 0
foreach ($j in $jobs) {
  if ($WhatIf) {
    Write-Output ("WHATIF {0} : {1} -> {2} ({3})" -f $j.kind, $j.src_rel, $j.dst_rel, $j.reason)
    $ok++
    continue
  }
  $parent = Split-Path -Parent $j.dst
  if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }
  if (Test-Path -LiteralPath $j.dst) { throw "DEST EXISTS after preflight: $($j.dst)" }
  # log preflight_ok before move
  Write-LogRow -Path $MoveLog -Map @{
    run_id         = $RunId
    plan_id        = $j.plan_id
    row_id         = $j.row_id
    timestamp_utc  = $ts
    src            = $j.src_rel
    dst            = $j.dst_rel
    kind           = $j.kind
    status         = 'preflight_ok'
    reason         = $j.reason
    error          = ''
    sha256_before  = ''
    sha256_after   = ''
  }
  try {
    Move-Item -LiteralPath $j.src -Destination $j.dst
    Write-LogRow -Path $MoveLog -Map @{
      run_id         = $RunId
      plan_id        = $j.plan_id
      row_id         = $j.row_id
      timestamp_utc  = $ts
      src            = $j.src_rel
      dst            = $j.dst_rel
      kind           = $j.kind
      status         = 'applied'
      reason         = $j.reason
      error          = ''
      sha256_before  = ''
      sha256_after   = ''
    }
    Write-Output ("OK {0} : {1} -> {2}" -f $j.kind, $j.src_rel, $j.dst_rel)
    $ok++
  } catch {
    Write-LogRow -Path $MoveLog -Map @{
      run_id         = $RunId
      plan_id        = $j.plan_id
      row_id         = $j.row_id
      timestamp_utc  = $ts
      src            = $j.src_rel
      dst            = $j.dst_rel
      kind           = $j.kind
      status         = 'failed'
      reason         = $j.reason
      error          = $_.Exception.Message
      sha256_before  = ''
      sha256_after   = ''
    }
    Write-Output "FAILED after partial apply at row $($j.row_id): $($_.Exception.Message)"
    Write-Output "applied: $ok (stopped)"
    Write-Output "move_log: $MoveLog"
    exit 4
  }
}

Write-Output "applied: $ok"
Write-Output "move_log: $MoveLog"
if ($WhatIf) { exit 0 }
exit 0
