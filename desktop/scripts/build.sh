#!/usr/bin/env bash
#
# Full macOS build: icons → Python sidecar → Tauri .app/.dmg.
# Output: src-tauri/target/release/bundle/dmg/*.dmg
set -euo pipefail
cd "$(dirname "$0")/.."                      # → desktop/
ROOT="$(cd .. && pwd)"
TRIPLE="$(rustc -vV 2>/dev/null | awk '/host/{print $2}')"

# 0) Load signing config (.signing/signing.env) if present → sign + notarize.
abspath() { case "$1" in /*) echo "$1";; *) echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")";; esac; }
if [ -f .signing/signing.env ]; then
  set -a; . .signing/signing.env; set +a
  # Tauri imports the cert from base64 in APPLE_CERTIFICATE.
  if [ -n "${APPLE_CERTIFICATE_PATH:-}" ] && [ -z "${APPLE_CERTIFICATE:-}" ] && [ -f "$APPLE_CERTIFICATE_PATH" ]; then
    export APPLE_CERTIFICATE="$(base64 -i "$APPLE_CERTIFICATE_PATH")"
  fi
  # Tauri needs an absolute path to the notary .p8.
  [ -n "${APPLE_API_KEY_PATH:-}" ] && export APPLE_API_KEY_PATH="$(abspath "$APPLE_API_KEY_PATH")"
  echo "→ signing: ${APPLE_SIGNING_IDENTITY:-<none>}  notarize: ${APPLE_API_KEY:+API key}${APPLE_ID:+Apple ID}"
else
  echo "→ no .signing/signing.env — building UNSIGNED (ad-hoc). See .signing/signing.env.example"
fi
# Updater signing key (createUpdaterArtifacts=true → tauri signs the .app.tar.gz).
if [ -z "${TAURI_SIGNING_PRIVATE_KEY:-}" ] && [ -f .signing/updater.key ]; then
  export TAURI_SIGNING_PRIVATE_KEY="$(cat .signing/updater.key)"
  export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:-}"
  echo "→ updater signing key loaded (.signing/updater.key)"
fi

# 1) App icons (from the template's app-icon.svg → png → tauri icon set).
if [ ! -f src-tauri/icons/icon.icns ]; then
  echo "→ generating icons"
  ICON_SRC=""
  if [ -f src-tauri/icon-source.png ]; then
    ICON_SRC="src-tauri/icon-source.png"                       # committed 1024 PNG (CI-friendly)
  elif [ -d "$ROOT/docs/node_modules/sharp" ]; then
    node -e "require('$ROOT/docs/node_modules/sharp')('$ROOT/assets/app-icon.svg').resize(1024,1024).png().toFile('.icon-1024.png')" \
      && ICON_SRC=".icon-1024.png"
  fi
  if [ -n "$ICON_SRC" ]; then npx --yes @tauri-apps/cli icon "$ICON_SRC";
  else echo "⚠️  no icon source — add src-tauri/icon-source.png (1024px) and rerun"; fi
fi

# 2) Python sidecar.
bash scripts/build-sidecar.sh

# 2b) Sign the sidecar with hardened runtime so notarization passes (Tauri then
#     signs the app around it). Skipped when no identity is configured.
if [ -n "${APPLE_SIGNING_IDENTITY:-}" ] && [ -n "$TRIPLE" ]; then
  echo "→ codesigning sidecar (hardened runtime)"
  codesign --force --options runtime --timestamp \
    --entitlements src-tauri/entitlements.plist \
    --sign "$APPLE_SIGNING_IDENTITY" \
    "src-tauri/binaries/serve-$TRIPLE" || echo "⚠️  sidecar codesign failed"
fi

# 3) Tauri build → .app + .dmg (signs + notarizes when the signing env is set).
npm install
npx --yes @tauri-apps/cli build

echo
echo "✓ Done. DMG:"
ls -1 src-tauri/target/release/bundle/dmg/*.dmg 2>/dev/null || echo "  (check src-tauri/target/release/bundle/)"
