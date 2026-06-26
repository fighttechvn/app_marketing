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

# Cross-platform bits: PyInstaller appends .exe on Windows and uses ';' (not ':')
# as the --add-data src/dest separator there; Tauri wants the sidecar named
# serve-<triple>.exe on Windows.
EXE=""; SEP=":"
case "$TRIPLE" in *windows*) EXE=".exe"; SEP=";";; esac

# PyInstaller is a NATIVE Windows exe under git-bash, so its path args need Windows
# paths (D:\...) not MSYS paths (/d/...). `np` converts them on Windows, no-op elsewhere.
if [ -n "$EXE" ]; then np() { cygpath -w "$1"; }; else np() { printf '%s' "$1"; }; fi

echo "→ target triple: $TRIPLE"
rm -rf "$STAGE"; mkdir -p "$STAGE"

# 1) Stage the Playground tool + server (no landing page, no docs).
#    serve.py is a thin entry; the real backend is the `server/` package.
cp "$ROOT/serve.py" "$ROOT/index.html" "$STAGE/"
cp -R "$ROOT/server" "$STAGE/server"
cp "$ROOT/listing.json" "$ROOT/listing-current.json" "$ROOT/listing-template.json" "$STAGE/"
cp -R "$ROOT/assets" "$STAGE/assets"

# 2) Python deps + PyInstaller.
"$PY" -m pip install --quiet --upgrade pyinstaller pyjwt cryptography paramiko \
      google-api-python-client google-auth google-auth-httplib2

"$PY" -m PyInstaller --clean --noconfirm --onefile --name serve \
  --paths "$(np "$STAGE")" \
  --add-data "$(np "$STAGE/index.html")${SEP}." \
  --add-data "$(np "$STAGE/listing.json")${SEP}." \
  --add-data "$(np "$STAGE/listing-current.json")${SEP}." \
  --add-data "$(np "$STAGE/listing-template.json")${SEP}." \
  --add-data "$(np "$STAGE/assets")${SEP}assets" \
  --collect-all googleapiclient \
  --collect-all google_auth_httplib2 \
  --collect-submodules google \
  --collect-submodules server \
  --collect-submodules paramiko \
  --collect-all nacl \
  --hidden-import jwt \
  --hidden-import paramiko \
  --hidden-import cryptography \
  --distpath "$(np "$DESKTOP/.pyi-dist")" --workpath "$(np "$DESKTOP/.pyi-work")" --specpath "$(np "$DESKTOP/.pyi-spec")" \
  "$(np "$DESKTOP/sidecar/app_sidecar.py")"

# 3) Place the sidecar with the target-triple suffix Tauri requires
#    (serve-<triple> on macOS/Linux, serve-<triple>.exe on Windows).
mkdir -p "$DESKTOP/src-tauri/binaries"
cp "$DESKTOP/.pyi-dist/serve$EXE" "$DESKTOP/src-tauri/binaries/serve-$TRIPLE$EXE"
chmod +x "$DESKTOP/src-tauri/binaries/serve-$TRIPLE$EXE" 2>/dev/null || true
echo "✓ sidecar → src-tauri/binaries/serve-$TRIPLE$EXE"
