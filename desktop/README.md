# Desktop app (Tauri + Python sidecar)

Packages the **Playground tool** into a native **macOS `.app` / `.dmg`**. Tauri
(Rust + system WebView) is the shell; `serve.py` is bundled by PyInstaller as a
**sidecar** that serves the tool (`/` + `/api/*`). Only the tool is bundled — not
the landing page or docs — so the app opens straight into the Playground.

```
desktop/
  src-tauri/            Tauri (Rust) shell
    tauri.conf.json     bundle config (externalBin: binaries/serve, dmg target)
    src/lib.rs          spawn sidecar → wait for "READY <url>" → open window
    capabilities/       permission to run the serve sidecar
    binaries/           serve-<triple>  (generated)
  sidecar/app_sidecar.py  seeds a writable data dir, runs serve.py
  frontend/             loading splash (Tauri frontendDist)
  scripts/              setup-prereqs.sh · build-sidecar.sh · build.sh
```

## How it runs

1. Tauri launches → spawns the `serve` sidecar with `--port 0 --data-dir <appData>`.
2. The sidecar **seeds** `~/Library/Application Support/vn.fighttech.storepreview/`
   from the bundled tool (first run only) — so writes (`.env`, `listing*.json`,
   `assets/new`, `assets/current`) land in a **writable** location, not the
   read-only `.app`.
3. `serve.py` binds a free port (127.0.0.1) and prints `READY http://127.0.0.1:<port>/`.
   With no landing page bundled, `/` serves the tool directly.
4. Tauri reads that line and opens the window on the local URL — same origin for
   UI + `/api/*`, so Sync / Test / Try template all work.

## Build

```bash
bash scripts/setup-prereqs.sh    # one-time: Rust, PyInstaller, Python deps, node
bash scripts/build.sh            # icons → sidecar (PyInstaller) → tauri build
# → src-tauri/target/release/bundle/dmg/*.dmg
```

Dev loop (no packaging):

```bash
./run_desktop.sh                    # opens the app window (builds the sidecar once if missing)
./run_desktop.sh --rebuild-sidecar  # force-rebuild the Python sidecar first
```

## Release to GitHub

```bash
./appdist.sh                 # build .dmg + publish to a GitHub Release
./appdist.sh --skip-build    # reuse the last build, just upload
GH_REPO=owner/repo ./appdist.sh v1.0.0   # custom repo + tag
```

Builds via `scripts/build.sh`, then `gh release create`/`upload` the `.dmg`
(tag defaults to `desktop-v<version>`, repo `fighttechvn/app_marketing`). Requires
an authenticated `gh` (`gh auth login`). Publishing is an outward action — it
uploads a public artifact.

## Notes

- **Node is not needed** for the desktop build — only the Playground tool is
  bundled (no docs). The runtime is Python (sidecar) + the WebView.
- **Heavy deps** (`cryptography`, `google-api-python-client`) are collected via
  PyInstaller `--collect-all` flags — test Sync / Test keys in the built app.
- **Code signing / notarization** is required for distribution to other Macs
  (Gatekeeper). Set `APPLE_SIGNING_IDENTITY` / notarization env for `tauri build`,
  or users must right-click → Open. See the Tauri macOS signing docs.
- App data dir: `~/Library/Application Support/vn.fighttech.storepreview/`.
