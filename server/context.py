"""Runtime config + the mutable active project ROOT, shared across the package."""
import os, sys

# SP_ROOT lets a packaged build (Tauri desktop sidecar) point the server at a
# writable data dir instead of the read-only app bundle. Defaults to the repo
# root (this file lives in <root>/server/, so two dirnames up).
HERE = os.environ.get("SP_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "8092"))

# ROOT is the active project folder — switchable at runtime via /api/open ("Open
# folder"). Kept here so every module reads the live value through root().
_ROOT = HERE
def root():      return _ROOT
def set_root(p):
    global _ROOT
    _ROOT = p
def cur():       return os.path.join(_ROOT, "assets", "current")
def home_html(): return os.path.join(_ROOT, "home.html")     # landing (umbrella only)
def docs_dist(): return os.path.join(_ROOT, "docs", "dist")  # built docs (umbrella only)

# File-content env keys: exported base64 (single line) so a .env is self-contained
# (no need to copy the .p8 / service-account JSON separately). Decoded on use.
FILE_B64 = {"ASC_KEY_P8": "ASC_KEY_P8_B64",
            "PLAYSTORE_SERVICE_ACCOUNT_JSON": "PLAYSTORE_SERVICE_ACCOUNT_JSON_B64"}

# Only the keys the Sync flow needs to call App Store Connect + Google Play.
# Signing/keystore/Firebase secrets are NEVER exported (kept server-side).
SYNC_KEYS = ["PORT", "ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_P8", "BUNDLE_ID",
             "PLAYSTORE_PACKAGE_NAME", "PLAYSTORE_SERVICE_ACCOUNT_JSON"]
