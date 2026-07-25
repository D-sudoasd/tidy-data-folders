<#
.SYNOPSIS
  Map-first inventory of a folder tree (depth-2 + extension histogram + document signals).
.PARAMETER Root
  Project root to inventory.
.PARAMETER Json
  Emit JSON instead of markdown-ish text.
.PARAMETER MaxDepthList
  How deep to list directory names (default 2).
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [switch]$Json,
  [int]$MaxDepthList = 2
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Root)) { throw "Root not found: $Root" }
$Root = (Resolve-Path -LiteralPath $Root).Path

function Get-DirListing {
  param([string]$Path, [int]$Depth, [int]$Max)
  $rows = @()
  Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $rel = $_.FullName.Substring($Root.Length).TrimStart('\')
    $rows += [pscustomobject]@{
      rel    = $rel
      kind   = $(if ($_.PSIsContainer) { 'dir' } else { 'file' })
      bytes  = $(if ($_.PSIsContainer) { $null } else { $_.Length })
    }
    if ($_.PSIsContainer -and $Depth -lt $Max) {
      $rows += Get-DirListing -Path $_.FullName -Depth ($Depth + 1) -Max $Max
    }
  }
  return $rows
}

$docExts = @('.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xlsm')
$files = @(Get-ChildItem -LiteralPath $Root -Recurse -File -Force -ErrorAction SilentlyContinue)
$fileCount = $files.Count
$totalBytes = ($files | Measure-Object -Property Length -Sum).Sum
if ($null -eq $totalBytes) { $totalBytes = 0 }

$ext = $files | Group-Object Extension | Sort-Object Count -Descending | ForEach-Object {
  [pscustomobject]@{ ext = $(if ($_.Name) { $_.Name.ToLowerInvariant() } else { '(none)' }); count = $_.Count }
}

$documentClass = @($files | Where-Object { $docExts -contains $_.Extension.ToLowerInvariant() })
$documentClassCount = $documentClass.Count

$publisherIdNameCount = 0
$junkNameCount = 0
foreach ($f in $documentClass) {
  $n = $f.Name
  if ($n -match '1-s2\.0-|^\d{5,}\.pdf$|^s\d{4,}-|metals-\d|main(\s*\(\d+\))?\.pdf$|Review_`?\d' ) {
    $publisherIdNameCount++
  }
  if ($n -match '^(main|data|数据|SAXS|temp|tmp|document|未命名)(\s*\(\d+\))?\.pdf$' -or $n.Length -le 12) {
    $junkNameCount++
  }
}

$mapNames = @('README.md','README_PROJECT_MAP.md','AGENTS.md','FILE_MAP.md','ARCHIVE_MAP.md')
$maps = @()
Get-ChildItem -LiteralPath $Root -Recurse -File -Force -ErrorAction SilentlyContinue |
  Where-Object { $mapNames -contains $_.Name -or $_.Name -like 'MOVE_LOG_*.csv' -or $_.Name -like 'PLACEMENT_AUDIT_*.md' -or $_.Name -like 'DOC_RENAME_PLAN*.csv' } |
  ForEach-Object { $maps += $_.FullName.Substring($Root.Length).TrimStart('\') }

$listing = Get-DirListing -Path $Root -Depth 1 -Max $MaxDepthList

# profile signals
$names = ($files | Select-Object -ExpandProperty Name) -join '|'
$extSet = ($ext | Select-Object -ExpandProperty ext) -join ' '
$profile = 'generic'
$pdfCount = 0
$pdfRow = $ext | Where-Object { $_.ext -eq '.pdf' } | Select-Object -First 1
if ($pdfRow) { $pdfCount = [int]$pdfRow.count }

if ($extSet -match '\.cbf' -and ($names -match 'texture|omega|\.esg')) { $profile = 'sxrd-texture' }
elseif ($names -match 'Az_|timestamp_aligned|peakfit|maud' -or $extSet -match '\.fit') { $profile = 'sxrd-tensile' }
elseif ($names -match 'Article_|Letter_|CURRENT') { $profile = 'manuscript-heavy' }
elseif ($Root -match 'Desktop|Downloads|桌面') { $profile = 'desktop-dump' }
elseif (
  $fileCount -gt 0 -and
  $documentClassCount -ge 5 -and
  ($documentClassCount / [double]$fileCount) -ge 0.5 -and
  ($publisherIdNameCount -ge 2 -or $junkNameCount -ge 2 -or $pdfCount -ge 8)
) { $profile = 'literature-dump' }

$phaseD = switch ($profile) {
  'literature-dump' { 'on' }
  'desktop-dump' { 'docs_bucket' }
  'manuscript-heavy' { 'references_only' }
  'sxrd-texture' { 'off' }
  'sxrd-tensile' { 'off' }
  default { 'optional' }
}

$result = [ordered]@{
  root                     = $Root
  file_count               = $fileCount
  total_bytes              = $totalBytes
  suggested_profile        = $profile
  phase_d_policy           = $phaseD
  document_class_count     = $documentClassCount
  publisher_id_name_count  = $publisherIdNameCount
  junk_doc_name_count      = $junkNameCount
  extensions               = @($ext)
  existing_maps            = @($maps)
  listing                  = @($listing)
}

if ($Json) {
  $result | ConvertTo-Json -Depth 6
  exit 0
}

Write-Output "# inventory: $Root"
Write-Output ""
Write-Output "- file_count: $fileCount"
Write-Output "- total_bytes: $totalBytes"
Write-Output "- suggested_profile: $profile"
Write-Output "- phase_d_policy: $phaseD"
Write-Output "- document_class_count: $documentClassCount"
Write-Output "- publisher_id_name_count: $publisherIdNameCount"
Write-Output "- junk_doc_name_count: $junkNameCount"
Write-Output ""
Write-Output "## extensions"
$ext | ForEach-Object { Write-Output ("- {0}: {1}" -f $_.ext, $_.count) }
Write-Output ""
Write-Output "## existing_maps"
if ($maps.Count -eq 0) { Write-Output "- (none)" } else { $maps | ForEach-Object { Write-Output "- $_" } }
Write-Output ""
Write-Output "## listing (depth <= $MaxDepthList)"
$listing | ForEach-Object {
  Write-Output ("- [{0}] {1}" -f $_.kind, $_.rel)
}
