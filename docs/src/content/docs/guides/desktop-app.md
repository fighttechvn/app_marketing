---
title: Build a macOS desktop app (Tauri)
description: Package the store-preview tool into a native macOS .app / .dmg with Tauri and a bundled Python (serve.py) sidecar — build steps and how it works.
sidebar:
  order: 6
---

**Packaging the tool as a macOS desktop app** uses **Tauri** (Rust + the system
WebView) as the shell and bundles `serve.py` as a **PyInstaller sidecar**. The
desktop app bundles **only the Playground tool** (`/` + `/api/*`) — not the landing
page or docs — so it opens straight into the tool. Everything lives in `desktop/`.

## How it works

1. Tauri launches and spawns the `serve` sidecar with `--port 0 --data-dir <appData>`.
2. The sidecar **seeds** `~/Library/Application Support/vn.fighttech.storepreview/`
   from the bundled tool on first run — so writes (`.env`, `listing*.json`,
   `assets/new`, `assets/current`) go to a **writable** dir, not the read-only `.app`.
3. `serve.py` binds a free port and prints `READY http://127.0.0.1:<port>/`. With no
   landing page bundled, `/` serves the tool directly.
4. Tauri reads that line and opens the window on the URL — same origin for UI and
   `/api/*`, so Sync / Test / Try template work exactly like `run.sh`.

Only the Playground tool is bundled, so **Node is not needed** for the desktop
build. The runtime is the Python sidecar + the WebView.

## Build

```bash
cd desktop
bash scripts/setup-prereqs.sh    # one-time: Rust, PyInstaller, Python deps, node
bash scripts/build.sh            # icons → sidecar (PyInstaller) → tauri build
# → src-tauri/target/release/bundle/dmg/*.dmg
```

| Script | Does |
| --- | --- |
| `setup-prereqs.sh` | Installs Rust (rustup), PyInstaller + Python store deps, node deps |
| `build-sidecar.sh` | Embeds the Playground tool, PyInstaller → `src-tauri/binaries/serve-<triple>` |
| `build.sh` | Icons + sidecar + `tauri build` → `.app` / `.dmg` |

## Gotchas

- **Heavy deps** (`cryptography`, `google-api-python-client`) are pulled in with
  PyInstaller `--collect-all` flags. After building, open the app and run **Test
  keys** to confirm the bundled Python can reach both store APIs.
- **Code signing / notarization** is required to run on other Macs without a
  Gatekeeper warning — set the Apple signing env for `tauri build`, or right-click
  → Open. See the Tauri macOS distribution docs.
- The window only appears after the sidecar prints `READY`; a loading splash shows
  meanwhile.

See [`desktop/README.md`](https://github.com/fighttechvn/app_marketing) for the full
layout.
