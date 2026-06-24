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
echo "→ launching desktop app (Tauri dev)…"
exec npx --yes @tauri-apps/cli dev
