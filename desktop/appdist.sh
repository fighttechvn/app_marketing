#!/usr/bin/env bash
#
# appdist.sh — build the macOS .dmg and publish it to a GitHub Release.
#
#   ./appdist.sh [tag]        build + upload (tag defaults to "desktop-v<version>")
#   ./appdist.sh --skip-build [tag]   reuse the last build, just upload
#
# Env:
#   GH_REPO    target repo (default: fighttechvn/app_marketing)
#   NOTES      release notes (default: auto)
#
# Requires: GitHub CLI `gh` (authenticated) + the build toolchain
# (run scripts/setup-prereqs.sh first). Publishing a release is an outward action —
# this uploads a public artifact, so review before running.
set -euo pipefail
cd "$(dirname "$0")"                          # → desktop/

SKIP_BUILD=0
if [ "${1:-}" = "--skip-build" ]; then SKIP_BUILD=1; shift; fi

VERSION="$(python3 -c "import json;print(json.load(open('src-tauri/tauri.conf.json'))['version'])")"
PRODUCT="$(python3 -c "import json;print(json.load(open('src-tauri/tauri.conf.json'))['productName'])")"
TAG="${1:-desktop-v$VERSION}"
REPO="${GH_REPO:-fighttechvn/app_marketing}"

command -v gh >/dev/null 2>&1 || { echo "✗ GitHub CLI (gh) not installed — https://cli.github.com/"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "✗ not logged in — run: gh auth login"; exit 1; }

# 1) Build the .dmg (unless reusing the last build).
if [ "$SKIP_BUILD" = "0" ]; then
  bash scripts/build.sh
fi

# 2) Locate the freshest .dmg.
DMG="$(ls -t src-tauri/target/release/bundle/dmg/*.dmg 2>/dev/null | head -1 || true)"
[ -n "$DMG" ] && [ -f "$DMG" ] || { echo "✗ no .dmg found — run without --skip-build"; exit 1; }
echo "→ artifact: $DMG"
echo "→ repo: $REPO   tag: $TAG"

# Signed+notarized when .signing/signing.env carries a Developer ID identity.
if grep -q '^APPLE_SIGNING_IDENTITY=.\+' .signing/signing.env 2>/dev/null; then
  SIGN_NOTE="Signed with Developer ID & notarized — opens without a Gatekeeper warning."
else
  SIGN_NOTE="Unsigned: right-click → Open on first launch if Gatekeeper warns."
fi
NOTES="${NOTES:-$PRODUCT $VERSION — macOS desktop build (Tauri + Python sidecar). $SIGN_NOTE}"

# 2b) Updater artifacts (auto-update): build latest.json from the signed .app.tar.gz
#     so the updater endpoint (releases/latest/download/latest.json) stays valid.
ASSETS=("$DMG")
B=src-tauri/target/release/bundle/macos
SIG_FILE="$B/AppPreview.app.tar.gz.sig"
if [ -f "$SIG_FILE" ] && [ -f "$B/AppPreview.app.tar.gz" ]; then
  URL="https://github.com/$REPO/releases/download/$TAG/AppPreview.app.tar.gz"
  python3 -c 'import json,sys; v,p,u,s,o=sys.argv[1:6]; open(o,"w").write(json.dumps({"version":v,"pub_date":p,"platforms":{"darwin-aarch64":{"signature":s,"url":u}}},indent=2))' \
    "$VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$URL" "$(cat "$SIG_FILE")" "$B/latest.json"
  ASSETS+=("$B/AppPreview.app.tar.gz" "$SIG_FILE" "$B/latest.json")
  echo "→ updater: latest.json + .app.tar.gz(.sig)"
else
  echo "⚠️  no updater .app.tar.gz(.sig) — auto-update manifest skipped (set TAURI_SIGNING_PRIVATE_KEY / .signing/updater.key)"
fi

# 3) Create the release if missing, else upload (clobber the same asset names).
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "→ release $TAG exists — uploading assets"
  gh release upload "$TAG" "${ASSETS[@]}" --repo "$REPO" --clobber
else
  echo "→ creating release $TAG"
  gh release create "$TAG" "${ASSETS[@]}" --repo "$REPO" --title "$PRODUCT $VERSION" --notes "$NOTES"
fi

echo "✓ published: https://github.com/$REPO/releases/tag/$TAG"
