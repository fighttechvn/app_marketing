#!/usr/bin/env bash
#
# appdist.sh — build the macOS .dmg(s) and publish them to a GitHub Release.
#
#   ./appdist.sh [tag]                  build the NATIVE slice + upload any prebuilt
#                                       other-arch .dmg present (default --arch both)
#   ./appdist.sh --arch arm64 [tag]     build/upload a single arch (must be native)
#   ./appdist.sh --arch intel [tag]
#   ./appdist.sh --skip-build [tag]     reuse the last build(s), just upload
#
# Uploads, per arch, the .dmg + the updater .app.tar.gz(.sig), plus a single
# combined latest.json (darwin-aarch64 + darwin-x86_64) so auto-update works on
# both Apple Silicon and Intel Macs. Tag defaults to "desktop-v<version>".
#
# IMPORTANT: only the slice matching the host arch is built locally — the Intel
# Python sidecar can't be cross-built on Apple Silicon (and vice-versa). The other
# slice's .dmg comes from CI (push to uat → macos-13 builds Intel). In `--arch both`
# the non-native slice is skipped with a warning unless its .dmg is already on disk
# (e.g. `gh release download` it next to the native one, then `--skip-build`).
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
ARCHSEL="both"
TAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-build) SKIP_BUILD=1; shift ;;
    --arch)       ARCHSEL="${2:-both}"; shift 2 ;;
    --arch=*)     ARCHSEL="${1#*=}"; shift ;;
    -h|--help)    sed -n '2,16p' "$0"; exit 0 ;;
    *)            TAG="$1"; shift ;;
  esac
done

case "$ARCHSEL" in
  both)              ARCHES="arm64 intel" ;;
  arm64|arm|aarch64) ARCHES="arm64" ;;
  intel|x86_64|x64)  ARCHES="intel" ;;
  *) echo "✗ --arch must be arm64 | intel | both"; exit 1 ;;
esac

VERSION="$(python3 -c "import json;print(json.load(open('src-tauri/tauri.conf.json'))['version'])")"
PRODUCT="$(python3 -c "import json;print(json.load(open('src-tauri/tauri.conf.json'))['productName'])")"
TAG="${TAG:-desktop-v$VERSION}"
REPO="${GH_REPO:-fighttechvn/app_marketing}"

command -v gh >/dev/null 2>&1 || { echo "✗ GitHub CLI (gh) not installed — https://cli.github.com/"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "✗ not logged in — run: gh auth login"; exit 1; }

# Per-arch metadata.
triple_of()   { case "$1" in arm64) echo aarch64-apple-darwin ;; intel) echo x86_64-apple-darwin ;; esac; }
platform_of() { case "$1" in arm64) echo darwin-aarch64       ;; intel) echo darwin-x86_64       ;; esac; }
# Updater asset name on the release. Intel is renamed so it never collides with
# the arm bundle (both are produced as AppPreview.app.tar.gz in their own dir).
updname_of()  { case "$1" in arm64) echo AppPreview.app.tar.gz ;; intel) echo AppPreview_x64.app.tar.gz ;; esac; }

HOST_ARCH="$(uname -m 2>/dev/null || echo "")"   # arm64 / x86_64
arch_native() { case "$1:$HOST_ARCH" in arm64:arm64|intel:x86_64) return 0;; *) return 1;; esac; }

ASSETS=()
PLATFORM_ARGS=()          # repeated triples: <platform> <url> <sigfile>
MULTI=0; [ "$ARCHES" = "arm64 intel" ] && MULTI=1

for A in $ARCHES; do
  TRIPLE="$(triple_of "$A")"
  BUNDLE="src-tauri/target/$TRIPLE/release/bundle"
  echo "──────── $A ($TRIPLE) ────────"
  if [ "$SKIP_BUILD" = "0" ]; then
    # The non-native macOS slice can't be cross-built locally (see build-sidecar.sh).
    # In 'both' mode just skip it with a note; a single explicit arch is an error.
    if ! arch_native "$A"; then
      MSG="$A can't be cross-built on a $HOST_ARCH Mac — build it via CI (push to uat → macos-13) or on an Intel Mac"
      if [ "$MULTI" = "1" ]; then echo "⚠️  skipping: $MSG"; continue; fi
      echo "✗ $MSG"; exit 1
    fi
    bash scripts/build.sh "$A"
  fi

  DMG="$(ls -t "$BUNDLE"/dmg/*.dmg 2>/dev/null | head -1 || true)"
  if [ -z "$DMG" ] || [ ! -f "$DMG" ]; then
    MSG="no $A .dmg in $BUNDLE/dmg"
    if [ "$MULTI" = "1" ]; then echo "⚠️  skipping: $MSG (build it on $A, or drop it from this release)"; continue; fi
    echo "✗ $MSG — build it (drop --skip-build)"; exit 1
  fi
  echo "→ $A dmg: $DMG"
  ASSETS+=("$DMG")

  # Updater bundle (auto-update). Stage under the release-facing name.
  TARBALL="$BUNDLE/macos/AppPreview.app.tar.gz"
  if [ -f "$TARBALL" ] && [ -f "$TARBALL.sig" ]; then
    UP="$(updname_of "$A")"
    STAGED="$BUNDLE/macos/$UP"
    if [ "$STAGED" != "$TARBALL" ]; then cp -f "$TARBALL" "$STAGED"; cp -f "$TARBALL.sig" "$STAGED.sig"; fi
    ASSETS+=("$STAGED" "$STAGED.sig")
    PLATFORM_ARGS+=("$(platform_of "$A")" "https://github.com/$REPO/releases/download/$TAG/$UP" "$STAGED.sig")
  else
    echo "⚠️  no $A updater .app.tar.gz(.sig) — auto-update for $A skipped (set .signing/updater.key / TAURI_SIGNING_PRIVATE_KEY)"
  fi
done

[ "${#ASSETS[@]}" -gt 0 ] || { echo "✗ nothing to publish — no .dmg was built/found for: $ARCHES"; exit 1; }

# Combined updater manifest.
if [ "${#PLATFORM_ARGS[@]}" -gt 0 ]; then
  LATEST="src-tauri/target/latest.json"
  python3 - "$VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LATEST" "${PLATFORM_ARGS[@]}" <<'PY'
import json, sys
ver, pub, out = sys.argv[1:4]
rest = sys.argv[4:]
platforms = {}
for i in range(0, len(rest), 3):
    name, url, sigf = rest[i:i+3]
    platforms[name] = {"signature": open(sigf).read().strip(), "url": url}
json.dump({"version": ver, "pub_date": pub, "platforms": platforms}, open(out, "w"), indent=2)
print("→ latest.json platforms:", ", ".join(platforms))
PY
  ASSETS+=("$LATEST")
fi

# Signed-vs-unsigned note.
if grep -q '^APPLE_SIGNING_IDENTITY=.\+' .signing/signing.env 2>/dev/null; then
  SIGN_NOTE="Signed with Developer ID & notarized — opens without a Gatekeeper warning."
else
  SIGN_NOTE="Unsigned: right-click → Open on first launch if Gatekeeper warns."
fi
NOTES="${NOTES:-$PRODUCT $VERSION — macOS desktop build (Apple Silicon + Intel). $SIGN_NOTE}"

echo "→ repo: $REPO   tag: $TAG"
echo "→ assets:"; printf '   %s\n' "${ASSETS[@]}"

# Create the release if missing, else upload (clobber the same asset names).
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "→ release $TAG exists — uploading assets"
  gh release upload "$TAG" "${ASSETS[@]}" --repo "$REPO" --clobber
else
  echo "→ creating release $TAG"
  gh release create "$TAG" "${ASSETS[@]}" --repo "$REPO" --title "$PRODUCT $VERSION" --notes "$NOTES"
fi

echo "✓ published: https://github.com/$REPO/releases/tag/$TAG"
