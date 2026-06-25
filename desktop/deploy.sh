#!/usr/bin/env bash
#
# deploy.sh — one-shot macOS release: make sure the signing assets are present,
# then package (sign + notarize) and publish the .dmg to a GitHub Release.
#
#   ./deploy.sh [tag]               ensure signing → build → publish
#   ./deploy.sh --skip-build [tag]  reuse the last build, just publish
#
# It checks for the private signing bundle in .signing/ (the working tree of
# the app_dist repo). If missing, it clones it; then imports the Developer ID
# cert into the keychain and hands off to appdist.sh.
#
# Env:
#   SIGN_REPO   private signing repo  (default: fighttechvn/app_marketing.app_dist)
#   GH_REPO     release target repo   (default: fighttechvn/app_marketing)
#
# Publishing a release is an outward action — review before running.
set -euo pipefail
cd "$(dirname "$0")"                          # → desktop/

SIGN_DIR=".signing"
SIGN_REPO="${SIGN_REPO:-fighttechvn/app_marketing.app_dist}"

# ── 1) Ensure the signing bundle (.app_dist) is present ──────────────────────
if [ -f "$SIGN_DIR/signing.env" ] && grep -q '^APPLE_SIGNING_IDENTITY=.\+' "$SIGN_DIR/signing.env"; then
  echo "✓ signing assets present ($SIGN_DIR/signing.env)"
else
  echo "→ $SIGN_DIR not set up — fetching private signing repo: $SIGN_REPO"
  command -v gh >/dev/null 2>&1 || { echo "✗ GitHub CLI (gh) required to clone the private signing repo — https://cli.github.com/"; exit 1; }
  gh auth status >/dev/null 2>&1 || { echo "✗ not logged in — run: gh auth login"; exit 1; }
  if [ -e "$SIGN_DIR" ] && [ ! -d "$SIGN_DIR/.git" ]; then
    # A non-repo .signing exists (e.g. only updater.key) — stash it, clone, restore.
    TMP="$(mktemp -d)"; mv "$SIGN_DIR" "$TMP/old"
    gh repo clone "$SIGN_REPO" "$SIGN_DIR" -- -q
    cp -n "$TMP/old/"* "$SIGN_DIR/" 2>/dev/null || true
    rm -rf "$TMP"
  else
    gh repo clone "$SIGN_REPO" "$SIGN_DIR" -- -q
  fi
  [ -f "$SIGN_DIR/signing.env" ] && grep -q '^APPLE_SIGNING_IDENTITY=.\+' "$SIGN_DIR/signing.env" \
    || { echo "✗ cloned $SIGN_REPO but no usable signing.env inside — check the repo contents"; exit 1; }
  echo "✓ cloned signing assets into $SIGN_DIR"
fi

# ── 2) Import the Developer ID cert into the login keychain (idempotent) ──────
# shellcheck disable=SC1091
set -a; . "$SIGN_DIR/signing.env"; set +a
if [ -n "${APPLE_SIGNING_IDENTITY:-}" ] \
   && ! security find-identity -v -p codesigning 2>/dev/null | grep -qF "$APPLE_SIGNING_IDENTITY"; then
  P12="${APPLE_CERTIFICATE_PATH:-$SIGN_DIR/DeveloperID.p12}"
  if [ -f "$P12" ]; then
    echo "→ importing signing cert into the login keychain"
    security import "$P12" -P "${APPLE_CERTIFICATE_PASSWORD:-}" -T /usr/bin/codesign >/dev/null 2>&1 \
      || echo "  (import returned non-zero — likely already present)"
  else
    echo "⚠️  cert file not found at $P12 — build.sh will try anyway"
  fi
fi
echo "→ identity: ${APPLE_SIGNING_IDENTITY:-<none>}   notarize: ${APPLE_API_KEY:+API key}${APPLE_ID:+Apple ID}"

# ── 3) Package + publish (build sign+notarize .dmg → GitHub Release) ──────────
exec bash appdist.sh "$@"
