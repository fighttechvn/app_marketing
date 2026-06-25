#!/usr/bin/env bash
#
# run_desktop.sh — run the desktop app in DEV mode (no .dmg packaging).
#
#   ./run_desktop.sh                    run it (builds the sidecar once if missing)
#   ./run_desktop.sh --rebuild-sidecar  force-rebuild the Python sidecar first
#
# Opens the native Tauri window: spawns the bundled serve.py sidecar, waits for
# READY, then loads the Playground. Needs the build toolchain — run
# scripts/setup-prereqs.sh first.
set -euo pipefail
cd "$(dirname "$0")"                          # → desktop/

TRIPLE="$(rustc -vV 2>/dev/null | awk '/host/{print $2}')"
[ -n "$TRIPLE" ] || { echo "✗ Rust not found — run: bash scripts/setup-prereqs.sh"; exit 1; }

# Tauri needs the sidecar binary (externalBin) present even in dev.
if [ "${1:-}" = "--rebuild-sidecar" ] || [ ! -f "src-tauri/binaries/serve-$TRIPLE" ]; then
  echo "→ building Python sidecar (serve-$TRIPLE)"
  bash scripts/build-sidecar.sh
fi

[ -d node_modules ] || npm install

# tauri.conf.json references src-tauri/icons/*, which are generated (not committed)
# from the committed icon-source.png. The .dmg build (scripts/build.sh) does this;
# dev mode must too, or generate_context!() fails to open icons/32x32.png.
if [ ! -f "src-tauri/icons/icon.icns" ] && [ -f "src-tauri/icon-source.png" ]; then
  echo "→ generating app icons (from icon-source.png)"
  npx --yes @tauri-apps/cli icon src-tauri/icon-source.png
fi
echo "→ launching desktop app (Tauri dev)…"
exec npx --yes @tauri-apps/cli dev
