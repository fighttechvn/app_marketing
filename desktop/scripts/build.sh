#!/usr/bin/env bash
#
# Full macOS build: icons → Python sidecar → Tauri .app/.dmg.
# Output: src-tauri/target/release/bundle/dmg/*.dmg
set -euo pipefail
cd "$(dirname "$0")/.."                      # → desktop/
ROOT="$(cd .. && pwd)"

# 1) App icons (from the template's app-icon.svg → png → tauri icon set).
if [ ! -f src-tauri/icons/icon.icns ]; then
  echo "→ generating icons"
  node -e "require('$ROOT/docs/node_modules/sharp')('$ROOT/assets/app-icon.svg').resize(1024,1024).png().toFile('.icon-1024.png')" \
    2>/dev/null || echo "⚠️  could not rasterize app-icon.svg — provide a 1024px PNG and rerun 'npx @tauri-apps/cli icon'"
  [ -f .icon-1024.png ] && npx --yes @tauri-apps/cli icon .icon-1024.png
fi

# 2) Python sidecar.
bash scripts/build-sidecar.sh

# 3) Tauri build → .app + .dmg.
npm install
npx --yes @tauri-apps/cli build

echo
echo "✓ Done. DMG:"
ls -1 src-tauri/target/release/bundle/dmg/*.dmg 2>/dev/null || echo "  (check src-tauri/target/release/bundle/)"
