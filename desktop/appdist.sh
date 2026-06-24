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

NOTES="${NOTES:-$PRODUCT $VERSION — macOS desktop build (Tauri + Python sidecar). Unsigned: right-click → Open on first launch if Gatekeeper warns.}"

# 3) Create the release if missing, else upload (clobber the same asset name).
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "→ release $TAG exists — uploading asset"
  gh release upload "$TAG" "$DMG" --repo "$REPO" --clobber
else
  echo "→ creating release $TAG"
  gh release create "$TAG" "$DMG" --repo "$REPO" --title "$PRODUCT $VERSION" --notes "$NOTES"
fi

echo "✓ published: https://github.com/$REPO/releases/tag/$TAG"
