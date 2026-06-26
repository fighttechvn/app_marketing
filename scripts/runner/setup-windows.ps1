<#
  setup-windows.ps1 — One-shot Windows setup for the desktop build box.

  Does two things:
    1) Enables OpenSSH Server (so the build can be driven remotely over SSH).
    2) Installs the build prerequisites for the Tauri + Python-sidecar app:
       VS C++ Build Tools, Rust (MSVC), WebView2, Node LTS, Python 3, Git.

  Run from an *elevated* PowerShell (Right-click → Run as administrator):

      Set-ExecutionPolicy -Scope Process Bypass -Force
      .\setup-windows.ps1                # SSH + all build prereqs
      .\setup-windows.ps1 -SshOnly       # just enable SSH (fast)
      .\setup-windows.ps1 -SkipSsh       # only build prereqs

  Idempotent: safe to re-run. Skips anything already installed.
#>
[CmdletBinding()]
param(
  [switch]$SshOnly,   # only enable OpenSSH Server, then exit
  [switch]$SkipSsh    # skip the SSH step, only install build prereqs
)

$ErrorActionPreference = "Stop"

function Info($m) { Write-Host "→ $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "✓ $m" -ForegroundColor Green }
function Warn($m) { Write-Host "! $m" -ForegroundColor Yellow }

# --- must be elevated -------------------------------------------------------
$admin = ([Security.Principal.WindowsPrincipal] `
  [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
  Warn "Not elevated. Right-click PowerShell → 'Run as administrator' and re-run."
  exit 1
}

# ===========================================================================
# 1) OpenSSH Server
# ===========================================================================
if (-not $SkipSsh) {
  Info "Enabling OpenSSH Server"

  $cap = Get-WindowsCapability -Online -Name OpenSSH.Server* |
         Where-Object State -ne 'Installed'
  if ($cap) {
    Info "installing OpenSSH.Server capability"
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
  } else {
    Ok "OpenSSH.Server already installed"
  }

  Set-Service -Name sshd -StartupType Automatic
  Start-Service sshd
  Ok "sshd running ($(Get-Service sshd | Select-Object -Expand Status))"

  # Firewall rule for port 22 (create only if missing).
  if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' `
      -DisplayName 'OpenSSH Server (sshd)' -Enabled True `
      -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
    Ok "firewall: opened TCP 22"
  } else {
    Ok "firewall: TCP 22 rule already present"
  }

  # Default the SSH shell to PowerShell (so remote commands behave predictably).
  $pwshExe = (Get-Command powershell.exe).Source
  New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value $pwshExe -PropertyType String -Force | Out-Null
  Ok "default SSH shell → $pwshExe"

  $ip = (Get-NetIPAddress -AddressFamily IPv4 |
         Where-Object { $_.IPAddress -notmatch '^(127|169\.254)' } |
         Select-Object -First 1 -Expand IPAddress)
  Ok "SSH ready. From the Mac:  ssh 'fighttech team@$ip'"

  if ($SshOnly) { Info "SshOnly set — done."; exit 0 }
}

# ===========================================================================
# 2) Build prerequisites  (needs winget — App Installer from the MS Store)
# ===========================================================================
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Warn "winget not found. Install 'App Installer' from the Microsoft Store, then re-run."
  Warn "Or install the tools manually: VS Build Tools (C++), Rust, Node LTS, Python 3, Git."
  exit 1
}

function Ensure-Winget($id, $extra = @()) {
  $installed = winget list --id $id -e 2>$null | Select-String $id
  if ($installed) { Ok "$id already installed"; return }
  Info "installing $id"
  winget install --id $id -e --accept-source-agreements --accept-package-agreements `
    --silent @extra
}

# Microsoft C++ Build Tools (MSVC) — required by Rust MSVC + WebView2 linking.
Ensure-Winget "Microsoft.VisualStudio.2022.BuildTools" @(
  "--override",
  "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
)

# WebView2 runtime (the Tauri webview host). Usually present on Win11.
Ensure-Winget "Microsoft.EdgeWebView2Runtime"

# Node LTS (Tauri CLI pulled via npx), Git (build scripts are bash → git-bash),
# Python 3 (the sidecar; PyInstaller).
Ensure-Winget "OpenJS.NodeJS.LTS"
Ensure-Winget "Git.Git"
Ensure-Winget "Python.Python.3.12"

# Rust via rustup, pinned to the MSVC toolchain Tauri needs on Windows.
if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) {
  Ensure-Winget "Rustlang.Rustup"
  Info "configuring rustup → stable-x86_64-pc-windows-msvc"
  $rustup = "$env:USERPROFILE\.cargo\bin\rustup.exe"
  if (Test-Path $rustup) {
    & $rustup default stable-x86_64-pc-windows-msvc
    & $rustup target add x86_64-pc-windows-msvc
  }
} else {
  Ok "rust already installed ($(rustc --version 2>$null))"
}

Write-Host ""
Ok "Setup complete."
Write-Host @"

Next steps (open a NEW terminal so PATH refreshes):
  1) Verify:   rustc --version ; node --version ; py -3 --version ; git --version
  2) Build (run from Git Bash, not PowerShell):
       cd desktop
       PYTHON='py -3' bash scripts/build.sh
     Output: desktop/src-tauri/target/release/bundle/  (.msi / .exe / .nsis)

Note: the bash build scripts expect 'python3'. On this box use:
       PYTHON='py -3' bash scripts/build-sidecar.sh
"@ -ForegroundColor Gray
