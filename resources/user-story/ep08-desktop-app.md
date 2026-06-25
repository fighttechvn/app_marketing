# EP08: Desktop App Distribution User Stories

Feature: a signed, notarized macOS/Windows desktop build (Tauri shell + PyInstaller Python sidecar) with auto-update.

## EP08.US001: Install and launch a native app
As a user, I want a double-click desktop app so that I can use App Preview without a terminal.

Acceptance criteria:
- A signed/notarized `.dmg` (macOS) and NSIS installer (Windows) install without Gatekeeper/SmartScreen blocks.
- On launch, the Tauri shell spawns the Python sidecar, waits for `READY http://127.0.0.1:<port>/`, and opens a native window on that URL.
- The bundled app serves the Playground directly at `/`; Sync/Test/Try-template work as in `run.sh`.

## EP08.US002: Keep app data isolated and seeded
As a user, I want my edits stored in a stable per-user location so that updates don't wipe my work.

Acceptance criteria:
- First run seeds `~/Library/Application Support/vn.fighttech.appstorepreview/` (or the platform equivalent) from the bundled tool.
- Writable: `.env`, `listing.json`, `listing-current.json`, `assets/new/`, `assets/current/`.
- The native File menu offers Open Folder and Check for Updates.

## EP08.US003: Receive automatic updates
As a user, I want the app to update itself so that I always have the latest version.

Acceptance criteria:
- The Tauri updater reads `latest.json` from the GitHub Release; updates are cryptographically signed and verified before install + relaunch.
- "Check for Updates" works on demand; a silent check runs on launch.
- CI builds and publishes signed artifacts on a version bump (macOS + Windows).

## EP08.US004: Build and sign from source
As a maintainer, I want a reproducible signed build so that I can cut releases.

Acceptance criteria:
- `desktop/scripts/build-sidecar.sh` embeds the Playground and PyInstaller-builds the backend binary.
- `desktop/scripts/build.sh` produces the `.app`/`.dmg`; signing uses a Developer ID cert + ASC API key for notarization (assets under `.signing/`).
- `deploy.sh` / `appdist.sh` build and publish to a GitHub Release (`.dmg`, `latest.json`, `.app.tar.gz`, `.sig`).
