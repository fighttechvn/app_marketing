#!/usr/bin/env python3
"""PyInstaller entry for the desktop sidecar.

The Playground tool (index.html + assets + listing*.json) + serve.py are bundled
into this binary (PyInstaller --add-data). The landing page and docs are NOT
bundled — the desktop app opens straight into the tool at "/".
On launch we seed a WRITABLE data dir (passed by Tauri as --data-dir) from the
read-only bundle, point serve.py at it via SP_ROOT, and run the server. serve.py
prints `READY http://127.0.0.1:<port>/`, which the Tauri shell reads to open the
window.

  app_sidecar --port 0 --data-dir "~/Library/Application Support/<app>"
"""
import argparse
import os
import shutil
import sys


def resource_root():
    """Bundled resources dir (PyInstaller) or this folder when run from source."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def seed(res, data):
    # Desktop app bundles ONLY the Playground tool (not the landing page or docs),
    # so serve.py serves the tool directly at "/". Seed just the tool's files.
    os.makedirs(data, exist_ok=True)
    for name in ("index.html",
                 "listing.json", "listing-current.json", "listing-template.json"):
        src, dst = os.path.join(res, name), os.path.join(data, name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
    src, dst = os.path.join(res, "assets"), os.path.join(data, "assets")
    if os.path.isdir(src) and not os.path.isdir(dst):
        shutil.copytree(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="0")
    ap.add_argument("--data-dir", required=True)
    args = ap.parse_args()

    res = resource_root()
    data = os.path.expanduser(args.data_dir)
    seed(res, data)

    # serve.py reads these at import time.
    os.environ["SP_ROOT"] = data
    os.environ["PORT"] = str(args.port)

    sys.path.insert(0, res)          # serve.py sits beside us in the bundle
    import serve
    serve.run()


if __name__ == "__main__":
    main()
