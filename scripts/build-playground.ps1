<#
.SYNOPSIS
  Build the Playground tool as a static, self-contained bundle (Windows).

.DESCRIPTION
  Assembles ONLY the Playground (the store-preview tool) into an output folder:

      <OutDir>/
        index.html
        listing.json  listing-current.json  listing-template.json
        assets/...

  This mirrors step 2 of scripts/build-pages.sh, but standalone and Windows-native.
  The tool uses RELATIVE paths for its data + assets, so the bundle works when
  served from any base path (e.g. /app_marketing/playground/ on GitHub Pages).

  NOTE: the backend features (Sync / Test keys / Try template / Open folder) call
  /api/* and only work behind the live server (run.sh / serve.py). In this static
  build they are inert by design — preview, New/Current toggle and Review Diff work.

.PARAMETER OutDir
  Output directory. Default: <repo>/dist/playground

.PARAMETER Zip
  Also produce <OutDir>.zip next to the output folder.

.PARAMETER Serve
  After building, serve the static bundle for a quick preview (no backend).

.PARAMETER Port
  Port for -Serve. Default: 8093

.EXAMPLE
  pwsh scripts/build-playground.ps1
  pwsh scripts/build-playground.ps1 -OutDir C:\out\pg -Zip
  pwsh scripts/build-playground.ps1 -Serve -Port 9000
#>
[CmdletBinding()]
param(
  [string]$OutDir,
  [switch]$Zip,
  [switch]$Serve,
  [int]$Port = 8093
)

$ErrorActionPreference = 'Stop'

# Repo root = parent of this script's folder (scripts/..)
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $RepoRoot 'dist\playground' }

Write-Host "-> Repo root : $RepoRoot"
Write-Host "-> Output    : $OutDir"

# Files that make up the static Playground (relative to repo root).
$files = @(
  'index.html',
  'listing.json',
  'listing-current.json',
  'listing-template.json'
)
$assetsDir = Join-Path $RepoRoot 'assets'

# Validate inputs before touching the output dir.
foreach ($f in $files) {
  $p = Join-Path $RepoRoot $f
  if (-not (Test-Path -LiteralPath $p)) { throw "missing required file: $f (run from the repo, or check the clone)" }
}
if (-not (Test-Path -LiteralPath $assetsDir)) { throw "missing required folder: assets/" }

# Clean + recreate output.
if (Test-Path -LiteralPath $OutDir) { Remove-Item -LiteralPath $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# 1) Copy the tool files.
foreach ($f in $files) {
  Copy-Item -LiteralPath (Join-Path $RepoRoot $f) -Destination (Join-Path $OutDir $f) -Force
  Write-Host "   + $f"
}

# 2) Copy assets/ recursively.
Copy-Item -LiteralPath $assetsDir -Destination (Join-Path $OutDir 'assets') -Recurse -Force
Write-Host "   + assets/ (recursive)"

# Report size.
$bytes = (Get-ChildItem -LiteralPath $OutDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
$count = (Get-ChildItem -LiteralPath $OutDir -Recurse -File | Measure-Object).Count
Write-Host ("OK  built {0} files, {1:N1} MB -> {2}" -f $count, ($bytes / 1MB), $OutDir)

# 3) Optional zip.
if ($Zip) {
  $zipPath = "$OutDir.zip"
  if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
  Compress-Archive -Path (Join-Path $OutDir '*') -DestinationPath $zipPath
  Write-Host "OK  zipped -> $zipPath"
}

# 4) Optional preview (static only — no /api backend).
if ($Serve) {
  $py = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
  if (-not $py) { throw "No Python 3 found to serve the preview. Install Python 3 or open index.html directly." }

  Write-Host ""
  Write-Host "-> Serving static preview at http://127.0.0.1:$Port/ (Ctrl+C to stop)"
  Write-Host "   (backend /api/* features are inert in a static build)"
  $env:PYTHONUTF8 = '1'
  & $py -m http.server $Port --bind 127.0.0.1 --directory $OutDir
}
