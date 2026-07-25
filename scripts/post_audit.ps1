<#
.SYNOPSIS
  Post-reorg audit with plan/log integrity checks (SHA when available).
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [int]$BeforeCount = -1,
  [int]$MaxNewFiles = 30,
  [switch]$RequireReadme,
  [string[]]$CheckPaths = @(),
  [string]$DocRenamePlan = '',
  [string]$AppliedLog = '',
  [switch]$FailOnEmptyDirs,
  [string]$Profile = '',
  [switch]$RequireDocRenamePlan,
  [switch]$RequireAppliedLog
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Root)) { throw "Root not found: $Root" }
$Root = (Resolve-Path -LiteralPath $Root).Path
$fail = 0
$enumErrors = 0

function Fail([string]$m) { $script:fail++; Write-Output "FAIL: $m" }
function Pass([string]$m) { Write-Output "PASS: $m" }
function Warn([string]$m) { Write-Output "WARN: $m" }

function Test-UnderRoot([string]$Full) {
  $fullN = [System.IO.Path]::GetFullPath($Full)
  $rootN = [System.IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
  return $fullN.StartsWith($rootN, [System.StringComparison]::OrdinalIgnoreCase) -or
    ($fullN.TrimEnd('\') -eq $Root.TrimEnd('\'))
}

function Get-FileSha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

Write-Output "# post_audit: $Root"

try {
  $files = @(Get-ChildItem -LiteralPath $Root -Recurse -File -Force -ErrorAction Stop)
} catch {
  Fail "directory enumeration failed: $($_.Exception.Message)"
  Write-Output "AUDIT_RESULT: FAIL ($fail)"
  exit 1
}
$after = $files.Count
Write-Output "- after_file_count: $after"

if ($BeforeCount -ge 0) {
  if ($after -lt $BeforeCount) {
    Fail "count seal dropped: before=$BeforeCount after=$after (summary only — not full integrity)"
  } elseif ($after -gt ($BeforeCount + $MaxNewFiles)) {
    Fail "count seal unexpected growth: before=$BeforeCount after=$after"
  } else {
    Pass "count summary before=$BeforeCount after=$after"
  }
}

# Doc rename plan: must exist if required; verify approved rows with SHA
if ($RequireDocRenamePlan -or $DocRenamePlan) {
  if (-not $DocRenamePlan) {
    Fail "DocRenamePlan path not provided"
  } elseif (-not (Test-Path -LiteralPath $DocRenamePlan)) {
    Fail "DocRenamePlan missing: $DocRenamePlan"
  } else {
    $planRows = @(Import-Csv -LiteralPath $DocRenamePlan)
    $checked = 0
    foreach ($r in $planRows) {
      $ap = [string]$r.approved
      if (@('true', 'yes', '1', 'y') -notcontains $ap.ToLowerInvariant()) { continue }
      $action = [string]$r.action
      if (@('rename', 'normalize', 'move_only') -notcontains $action) { continue }
      $dst = [string]$r.dst
      $srcHash = ([string]$r.src_sha256).ToLowerInvariant()
      if ($dst.Contains('..') -or [System.IO.Path]::IsPathRooted($dst)) {
        Fail "plan dst unsafe: $dst"
        continue
      }
      $full = Join-Path $Root ($dst -replace '/', '\')
      if (-not (Test-UnderRoot $full)) {
        Fail "plan dst outside root: $dst"
        continue
      }
      if (-not (Test-Path -LiteralPath $full)) {
        Fail "approved plan dst missing: $dst"
        continue
      }
      if ($srcHash -and $srcHash -match '^[0-9a-f]{64}$') {
        try {
          $h = Get-FileSha256 $full
          if ($h -ne $srcHash) {
            Fail "SHA mismatch at $dst (plan src_sha256 != file)"
            continue
          }
        } catch {
          Fail "cannot hash $dst : $($_.Exception.Message)"
          continue
        }
      } else {
        Fail "approved plan row missing src_sha256 for $dst"
        continue
      }
      $checked++
    }
    if ($checked -gt 0) { Pass "approved plan destinations SHA-ok: $checked" }
    else { Warn "no approved executable rows in DocRenamePlan" }
  }
}

# Applied log
if ($RequireAppliedLog -or $AppliedLog) {
  if (-not $AppliedLog) {
    Fail "AppliedLog path not provided"
  } elseif (-not (Test-Path -LiteralPath $AppliedLog)) {
    Fail "AppliedLog missing: $AppliedLog"
  } else {
    try {
      $logRows = @(Import-Csv -LiteralPath $AppliedLog)
      $ok = 0
      $failedStatuses = 0
      foreach ($r in $logRows) {
        $st = ([string]$r.status).ToLowerInvariant()
        if ($st -in @('failed', 'partial', 'rollback_failed')) {
          Fail "log status=$st row_id=$($r.row_id) src=$($r.src) error=$($r.error)"
          $failedStatuses++
          continue
        }
        if ($st -and $st -ne 'applied') { continue }
        $dst = [string]$r.dst
        if ([string]::IsNullOrWhiteSpace($dst) -or $dst -like '(removed*') { continue }
        if ($dst.Contains('..')) { Fail "log dst unsafe: $dst"; continue }
        $full = if ([System.IO.Path]::IsPathRooted($dst)) { $dst } else { Join-Path $Root ($dst -replace '/', '\') }
        if (-not (Test-UnderRoot $full)) { Fail "log dst outside root: $dst"; continue }
        if (-not (Test-Path -LiteralPath $full)) { Fail "applied log dst missing: $dst"; continue }
        $afterHash = ([string]$r.sha256_after).ToLowerInvariant()
        $beforeHash = ([string]$r.sha256_before).ToLowerInvariant()
        if ($afterHash -match '^[0-9a-f]{64}$') {
          try {
            $h = Get-FileSha256 $full
            if ($h -ne $afterHash) {
              Fail "log sha256_after mismatch at $dst"
              continue
            }
            if ($beforeHash -match '^[0-9a-f]{64}$' -and $beforeHash -ne $afterHash) {
              Fail "log sha256_before != sha256_after at $dst (unexpected for rename)"
              continue
            }
          } catch {
            Fail "cannot hash log dst $dst : $($_.Exception.Message)"
            continue
          }
        }
        $ok++
      }
      if ($ok -gt 0) { Pass "applied log destinations present: $ok" }
      if ($failedStatuses -eq 0) { Pass "no failed statuses in AppliedLog" }
    } catch {
      Fail "cannot read AppliedLog: $($_.Exception.Message)"
    }
  }
}

# root purity — broader extensions
$rootFiles = @(Get-ChildItem -LiteralPath $Root -File -Force -ErrorAction Stop)
$allowedRootNames = @('README.md', 'AGENTS.md', 'FILE_MAP.md', 'TIDY_FOLDER_MAP.md')
$bulkExt = @(
  '.cbf', '.esg', '.fit', '.par', '.cif', '.npy', '.opju', '.zip', '.rar', '.7z',
  '.csv', '.tsv', '.xlsx', '.xlsm', '.ppt', '.pptx', '.json', '.h5', '.dat',
  '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exe', '.dll', '.msi', '.py', '.ps1'
)
if ($Profile -eq 'literature-dump') {
  $bulkExt += @('.pdf', '.docx', '.doc')
}
$bad = @($rootFiles | Where-Object {
    $n = $_.Name
    if ($n -like 'MOVE_LOG_*') { return $false }
    if ($n -like 'PLACEMENT_AUDIT_*') { return $false }
    if ($allowedRootNames -contains $n) { return $false }
    $e = $_.Extension.ToLowerInvariant()
    return ($bulkExt -contains $e)
  })
if ($bad.Count -gt 0) {
  Fail ("root purity: " + (($bad | ForEach-Object { $_.Name }) -join ', '))
} else {
  Pass "root purity"
}

if ($Profile -eq 'literature-dump') {
  $junk = @($rootFiles | Where-Object {
      $_.Name -match '^(main(\s*\(\d+\))?\.pdf|1-s2\.0-)'
    })
  if ($junk.Count -gt 0) {
    Fail ("literature junk names at root: " + (($junk | ForEach-Object { $_.Name }) -join ', '))
  } else {
    Pass "no publisher-junk names at root"
  }
}

# README open-first: prefer table after 先看哪里
$readme = Join-Path $Root 'README.md'
$mapAlt = Join-Path $Root 'TIDY_FOLDER_MAP.md'
$entryFile = $null
if (Test-Path -LiteralPath $readme) { $entryFile = $readme }
elseif (Test-Path -LiteralPath $mapAlt) { $entryFile = $mapAlt }

if ($RequireReadme) {
  if (-not (Test-Path -LiteralPath $readme) -and -not (Test-Path -LiteralPath $mapAlt)) {
    Fail "README.md / TIDY_FOLDER_MAP.md missing"
  } else {
    Pass "map file present"
  }
}

if ($entryFile) {
  $lines = Get-Content -LiteralPath $entryFile -Encoding utf8 -ErrorAction SilentlyContinue
  $inOpen = $false
  $foundEntry = $false
  foreach ($line in $lines) {
    if ($line -match '先看哪里|Open-first|open-first') { $inOpen = $true; continue }
    if ($inOpen -and $line -match '^\s*\|') {
      # data row with backticks
      if ($line -match '`([^`]+)`') {
        $cand = $Matches[1] -replace '/', '\'
        if ($cand -match '\.[a-zA-Z0-9]+$' -and -not $cand.Contains('..')) {
          $fp = Join-Path $Root $cand
          if ((Test-UnderRoot $fp) -and (Test-Path -LiteralPath $fp)) {
            Pass "open-first entry exists: $cand"
            $foundEntry = $true
            break
          }
        }
      }
    }
    if ($inOpen -and $line -match '^#{1,3}\s') { break }
  }
  if (-not $foundEntry) {
    # fallback first backticked file path in file
    foreach ($line in $lines) {
      if ($line -match '`([^`]+\.[a-zA-Z0-9]+)`') {
        $cand = $Matches[1] -replace '/', '\'
        if ($cand.Contains('..')) { continue }
        $fp = Join-Path $Root $cand
        if ((Test-UnderRoot $fp) -and (Test-Path -LiteralPath $fp)) {
          Pass "README entry exists: $cand"
          $foundEntry = $true
          break
        }
      }
    }
  }
  if (-not $foundEntry) { Warn "could not auto-verify open-first path" }
}

foreach ($p in $CheckPaths) {
  if ([string]::IsNullOrWhiteSpace($p)) { continue }
  if ([System.IO.Path]::IsPathRooted($p) -or $p.Contains('..')) {
    Fail "CheckPaths must be relative under root: $p"
    continue
  }
  $full = Join-Path $Root $p
  if (-not (Test-UnderRoot $full)) { Fail "check path outside root: $p"; continue }
  if (Test-Path -LiteralPath $full) { Pass "check path: $p" }
  else { Fail "check path missing: $p" }
}

# empty directories (preserve known slots as warn only)
$preserveEmpty = @('to_sort', '00_docs', 'docs', '01_papers', '02_other_docs', '03_figures_exports', '99_archive')
$empties = @()
try {
  Get-ChildItem -LiteralPath $Root -Recurse -Directory -Force -ErrorAction Stop | ForEach-Object {
    try {
      $k = @(Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction Stop)
      if ($k.Count -eq 0) {
        $rel = $_.FullName.Substring($Root.Length).TrimStart('\')
        $leaf = Split-Path -Leaf $_.FullName
        if ($preserveEmpty -contains $leaf) { return }
        $empties += $rel
      }
    } catch {
      $script:enumErrors++
      Fail "cannot list dir: $($_.FullName.Substring($Root.Length).TrimStart('\'))"
    }
  }
} catch {
  Fail "empty-dir scan failed: $($_.Exception.Message)"
}

if ($empties.Count -gt 0) {
  $msg = "empty dirs ($($empties.Count)): $($empties -join '; ')"
  if ($FailOnEmptyDirs -or $Profile -eq 'literature-dump') { Fail $msg }
  else { Warn $msg }
} else {
  Pass "no empty directories (excluding preserved slots)"
}

if ($enumErrors -gt 0) {
  Fail "directory enum errors: $enumErrors"
}

Write-Output "- AGENTS.md: $(Test-Path (Join-Path $Root 'AGENTS.md'))"
Write-Output "- docs/ARCHIVE_MAP.md: $(Test-Path (Join-Path $Root 'docs\ARCHIVE_MAP.md'))"

if ($fail -gt 0) {
  Write-Output "AUDIT_RESULT: FAIL ($fail)"
  exit 1
}
Write-Output "AUDIT_RESULT: PASS"
exit 0
