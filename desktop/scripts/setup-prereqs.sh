#!/usr/bin/env bash
#
# One-time prerequisites for building the macOS desktop app.
set -euo pipefail

echo "→ Xcode command line tools"; xcode-select -p >/dev/null 2>&1 || xcode-select --install || true

if ! command -v rustc >/dev/null 2>&1; then
  echo "→ installing Rust (rustup)"
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  # shellcheck disable=SC1090
  . "$HOME/.cargo/env"
fi

echo "→ Python deps + PyInstaller"
python3 -m pip install --upgrade pyinstaller pyjwt cryptography \
  google-api-python-client google-auth google-auth-httplib2

echo "→ Node deps (Tauri CLI is pulled via npx)"
( cd "$(dirname "$0")/.." && npm install )

cat <<'EOF'

✓ Prereqs ready. Build with:
    cd desktop && bash scripts/build.sh           # native (host) arch
Publish to a GitHub Release (builds the native slice; the other arch comes from CI):
    cd desktop && ./deploy.sh
Note: the Intel slice is built by CI (push to uat → macos-13); it can't be
cross-built on Apple Silicon (Python crypto deps need a native x86_64 toolchain).
EOF
