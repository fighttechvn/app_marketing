#!/usr/bin/env bash
#
# Build the Python backend (serve.py) into a single self-contained binary and
# place it where Tauri expects the sidecar: src-tauri/binaries/serve-<triple>.
# The desktop app bundles ONLY the Playground tool (index.html, listing*.json,
# assets/) — not the landing page or docs; the sidecar seeds a writable data dir
# from it at run, and serve.py serves the tool directly at "/".
set -euo pipefail
cd "$(dirname "$0")/.."                      # → desktop/
DESKTOP="$(pwd)"
ROOT="$(cd .. && pwd)"                        # → template root (the store-preview tool)
TRIPLE="$(rustc -vV | awk '/host/{print $2}')"
[ -n "$TRIPLE" ] || { echo "✗ rustc not found — install Rust (see setup-prereqs.sh)"; exit 1; }
STAGE="$DESKTOP/.sidecar-build"
PY="${PYTHON:-python3}"

echo "→ target triple: $TRIPLE"
rm -rf "$STAGE"; mkdir -p "$STAGE"

# 1) Stage the Playground tool + server (no landing page, no docs).
cp "$ROOT/serve.py" "$ROOT/index.html" "$STAGE/"
cp "$ROOT/listing.json" "$ROOT/listing-current.json" "$ROOT/listing-template.json" "$STAGE/"
cp -R "$ROOT/assets" "$STAGE/assets"

# 2) Python deps + PyInstaller.
"$PY" -m pip install --quiet --upgrade pyinstaller pyjwt cryptography \
      google-api-python-client google-auth google-auth-httplib2

"$PY" -m PyInstaller --clean --noconfirm --onefile --name serve \
  --paths "$STAGE" \
  --add-data "$STAGE/index.html:." \
  --add-data "$STAGE/listing.json:." \
  --add-data "$STAGE/listing-current.json:." \
  --add-data "$STAGE/listing-template.json:." \
  --add-data "$STAGE/assets:assets" \
  --collect-all googleapiclient \
  --collect-all google_auth_httplib2 \
  --collect-submodules google \
  --hidden-import jwt \
  --hidden-import cryptography \
  --distpath "$DESKTOP/.pyi-dist" --workpath "$DESKTOP/.pyi-work" --specpath "$DESKTOP/.pyi-spec" \
  "$DESKTOP/sidecar/app_sidecar.py"

# 3) Place the sidecar with the target-triple suffix Tauri requires.
mkdir -p "$DESKTOP/src-tauri/binaries"
cp "$DESKTOP/.pyi-dist/serve" "$DESKTOP/src-tauri/binaries/serve-$TRIPLE"
chmod +x "$DESKTOP/src-tauri/binaries/serve-$TRIPLE"
echo "✓ sidecar → src-tauri/binaries/serve-$TRIPLE"
