<#
.SYNOPSIS
  Find text files under Root that contain OldRoots path strings (report only).
.PARAMETER Root
  Project root to scan.
.PARAMETER OldRoots
  One or more absolute path prefixes to search for (e.g. previous layout roots).
.PARAMETER IncludeCurrentRoot
  Also search for the current Root string (default: true).
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [string[]]$OldRoots = @(),
  [switch]$IncludeCurrentRoot,
  [int]$MaxHitsPerFile = 3
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Root)) { throw "Root not found: $Root" }
$Root = (Resolve-Path -LiteralPath $Root).Path
if (-not $PSBoundParameters.ContainsKey('IncludeCurrentRoot')) { $IncludeCurrentRoot = $true }

$needles = [System.Collections.Generic.List[string]]::new()
if ($IncludeCurrentRoot) { $needles.Add($Root) }
foreach ($o in $OldRoots) {
  if ($o) { $needles.Add($o) }
}
# also variant with forward slashes
$extra = @()
foreach ($n in $needles) {
  $extra += ($n -replace '\\', '/')
  $extra += ($n -replace '\\', '\\')  # json-escaped style already in file as \\
}
foreach ($e in $extra) { if ($e -and -not $needles.Contains($e)) { $needles.Add($e) } }

$textExt = @('.json','.yaml','.yml','.md','.txt','.csv','.ps1','.py','.ins','.log','.html','.xml','.toml','.ini','.cfg')
$files = Get-ChildItem -LiteralPath $Root -Recurse -File -Force -ErrorAction SilentlyContinue |
  Where-Object { $textExt -contains $_.Extension.ToLowerInvariant() -or $_.Extension -eq '' }

$hits = @()
foreach ($f in $files) {
  # skip huge files
  if ($f.Length -gt 8MB) { continue }
  try {
    $content = Get-Content -LiteralPath $f.FullName -Raw -ErrorAction Stop
  } catch { continue }
  if ([string]::IsNullOrEmpty($content)) { continue }
  foreach ($n in $needles) {
    if ([string]::IsNullOrEmpty($n)) { continue }
    if ($content.IndexOf($n, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
      $rel = $f.FullName.Substring($Root.Length).TrimStart('\')
      $class = 'other'
      $name = $f.Name.ToLowerInvariant()
      if ($name -match 'batch|config|manifest|processing_manifest|calibration') { $class = 'config' }
      elseif ($name -match 'agent_result|texture_status|agent_summary|\.log$') { $class = 'historical' }
      elseif ($name -match 'readme|agents|archive_map|file_map') { $class = 'map' }
      $action = switch ($class) {
        'config' { 'rewrite' }
        'historical' { 'leave+note' }
        'map' { 'rewrite-if-stale' }
        default { 'review' }
      }
      $hits += [pscustomobject]@{
        file   = $rel
        class  = $class
        action = $action
        needle = $n
        bytes  = $f.Length
      }
      break
    }
  }
}

Write-Output "# path_refs: $Root"
Write-Output "- needles: $($needles -join ' | ')"
Write-Output "- hit_files: $($hits.Count)"
Write-Output ""
$hits | Sort-Object action, file | ForEach-Object {
  Write-Output ("- [{0}/{1}] {2}" -f $_.class, $_.action, $_.file)
}

# also JSON for agents
$jsonPath = Join-Path $env:TEMP ("tidy_path_refs_{0}.json" -f [guid]::NewGuid().ToString('N'))
$hits | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $jsonPath -Encoding utf8
Write-Output ""
Write-Output "json_sidecar: $jsonPath"
