# run.ps1 — Windows launcher for the store-preview server.
#
#   .\run.ps1            serve on http://127.0.0.1:8092/
#
# The bash run.sh is macOS/Linux only (lsof, open). On this machine `python` is
# Python 2.7 and `python3` is the broken Microsoft Store stub, so we launch via
# the `py -3` launcher explicitly.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Load PORT from .env if present (default 8092).
$port = 8092
if (Test-Path ".env") {
  $m = Select-String -Path ".env" -Pattern '^\s*PORT\s*=\s*(\d+)' | Select-Object -First 1
  if ($m) { $port = [int]$m.Matches[0].Groups[1].Value }
}

# Free the port if a stale listener is holding it.
$conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
  Write-Host "-> port $port busy; stopping existing listener (PID $($conn.OwningProcess))"
  Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}

$env:PORT = "$port"
$env:PYTHONIOENCODING = "utf-8"   # avoid cp1252 crash on the console log line

Write-Host ""
Write-Host "  Store Preview — http://127.0.0.1:$port/"
Write-Host "  (Ctrl+C to stop)"
Write-Host ""

Start-Process "http://127.0.0.1:$port/"
& py -3 serve.py
