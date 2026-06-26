#!/usr/bin/env bash
#
# Full macOS build: icons → Python sidecar → Tauri .app/.dmg.
#
#   build.sh                 build for the host arch (default — unchanged for CI)
#   build.sh arm64           build the Apple-Silicon slice  (aarch64-apple-darwin)
#   build.sh intel           build the Intel slice          (x86_64-apple-darwin)
#   build.sh --target <triple>
#
# Output (host):   src-tauri/target/release/bundle/dmg/*.dmg
# Output (target): src-tauri/target/<triple>/release/bundle/dmg/*.dmg
set -euo pipefail
cd "$(dirname "$0")/.."                      # → desktop/
ROOT="$(cd .. && pwd)"

# Optional cross-target. No arg → native host build (what CI uses).
TARGET_TRIPLE=""
case "${1:-}" in
  "")                                       ;;
  --target)        TARGET_TRIPLE="${2:-}"   ;;
  arm64|aarch64|aarch64-apple-darwin)  TARGET_TRIPLE="aarch64-apple-darwin" ;;
  intel|x86_64|x64|x86_64-apple-darwin) TARGET_TRIPLE="x86_64-apple-darwin" ;;
  *) echo "✗ unknown target '$1' — use: arm64 | intel | --target <triple>"; exit 1 ;;
esac

HOST_TRIPLE="$(rustc -vV 2>/dev/null | awk '/host/{print $2}')"
TRIPLE="${TARGET_TRIPLE:-$HOST_TRIPLE}"      # arch the sidecar + app are built for
if [ -n "$TARGET_TRIPLE" ]; then
  export TARGET_TRIPLE                       # build-sidecar.sh reads this
  BUNDLE="src-tauri/target/$TARGET_TRIPLE/release/bundle"
  # Make sure the Rust std for the target is present (e.g. Intel on Apple Silicon).
  if command -v rustup >/dev/null 2>&1 && ! rustup target list --installed 2>/dev/null | grep -qx "$TARGET_TRIPLE"; then
    echo "→ adding rust target $TARGET_TRIPLE"; rustup target add "$TARGET_TRIPLE"
  fi
else
  BUNDLE="src-tauri/target/release/bundle"
fi
echo "→ building for: $TRIPLE"

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
#    Pass --target only for an explicit cross-build so the default host build is
#    byte-for-byte what CI runs.
#
#    CI=true makes Tauri's bundle_dmg.sh skip the Finder/AppleScript layout step —
#    that step needs GUI automation access and fails in a headless/background/SSH
#    shell (leaving a leftover rw.*.dmg). GitHub Actions sets CI automatically; set
#    it here too so local builds package the .dmg the same way. Honor a preset CI.
export CI="${CI:-true}"
npm install
if [ -n "$TARGET_TRIPLE" ]; then
  npx --yes @tauri-apps/cli build --target "$TARGET_TRIPLE"
else
  npx --yes @tauri-apps/cli build
fi

echo
echo "✓ Done. DMG:"
ls -1 "$BUNDLE"/dmg/*.dmg 2>/dev/null || echo "  (check $BUNDLE/)"
