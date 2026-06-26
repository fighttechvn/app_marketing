# Changelog

All notable changes to the **App Preview** macOS desktop app. Releases are tagged
`desktop-v<version>` and published to
[GitHub Releases](https://github.com/fighttechvn/app_marketing/releases).

## 0.4.6 — 2026-06-26

**Remote iOS device control + Runners.**

### Added
- **Remote iOS control over SSH.** Drive a physical iPhone/iPad attached to
  another machine straight from the Playground — tap, swipe and mirror over an
  SSH connection to a "runner" host. A Runners/Settings dialog adds hosts, picks
  password or SSH-key auth, and tests the connection before use.
- **Runner sharing.** Export/import the runner list as JSON, plus an
  "Initial Runner" action that shares the current machine's SSH config as JSON
  so another operator can import it in one step.

### Fixed
- iOS 26: remote tap now uses W3C pointer actions (the legacy `/wda/tap/0`
  endpoint returns 500 there).
- Android: the emulator launch resolves the modern emulator `.exe` on Windows
  instead of the legacy path.
- Toolbar: the Settings gear is pinned to the top-right and the preview rail no
  longer overlaps it; all controls stay on one line.
- Windows: the server no longer crashes at startup on a non-UTF-8 console.

## 0.4.5 — 2026-06-26

**Build-pipeline maintenance.**

### Changed
- Multi-arch aware local build/publish scripts; set `CI=true` for local `.dmg`
  packaging so it matches CI (no functional app changes).

## 0.4.4 — 2026-06-26

**Build-pipeline maintenance.**

### Changed
- Build a separate Intel (x86_64) macOS `.dmg` alongside the Apple-Silicon
  slice (no functional app changes).

## 0.4.3 — 2026-06-26

**Ships the Windows launch fix to users.**

### Changed
- Version bump to publish fresh signed macOS `.dmg` and Windows NSIS `.exe`
  builds via the auto-release pipeline. The `0.4.2` bump never produced a
  release, so this is the first build that actually delivers the Windows
  launch fix below (no further functional changes to the app).

## 0.4.2 — 2026-06-25

**Windows launch fix.**

### Fixed
- Windows build showed a blank window / `127.0.0.1 refused to connect` shortly after
  launch. The Tauri shell stopped draining the sidecar's output after reading the
  `READY` line, so the Python server's stdout/stderr pipe filled and the server
  stalled/exited on Windows. The shell now keeps draining output for the app's
  lifetime and owns the sidecar process for the whole session; the server also no
  longer logs each request to stderr. The `READY` line is matched precisely so an
  unrelated log line can't open the window on the wrong URL.

## 0.4.1 — 2026-06-25

**Maintenance release — rebuild macOS + Windows installers.**

### Changed
- Version bump to publish fresh signed macOS `.dmg` and Windows NSIS `.exe`
  builds via the auto-release pipeline (no functional changes to the app).

## 0.3.0 — 2026-06-25

**Playground preview panel + real-device mirroring.**

### Added
- **Preview panel** (right-side icon rail) with Web / Media / Markdown previews.
- **Android mirror + remote control** via `adb` (click→tap, drag→swipe, keys, buttons)
  plus a native `scrcpy` launcher.
- **iPhone mirror + remote control** via WebDriverAgent over an `iproxy` USB tunnel
  (MJPEG stream, tap/swipe/button/text).
- Shared touch-feedback layer (ripple on tap, trail on swipe) for both platforms.
- New localhost-only backend routes (`/api/adb/*`, `/api/wda/*`, `/api/preview-file`)
  in a refactored `server/` package; binaries resolved via `ANDROID_HOME`/SDK/Homebrew
  fallbacks for GUI-launched apps.

### Fixed
- `run_desktop.sh` auto-generates the Tauri icon set in dev (fresh checkouts failed on a
  missing `icons/32x32.png`).

## 0.2.0 — 2026-06-25

**Signed & notarized builds + one-command deploy.**

### Added
- **Developer ID signing + Apple notarization** — the `.dmg` is now signed and
  notarized, so it opens on any Mac with **no Gatekeeper "damaged" warning**.
- **`deploy.sh`** — one-shot release: ensures the signing assets are present
  (clones the private `app_dist` repo if missing), imports the cert, then builds
  and publishes the `.dmg` to a GitHub Release.
- **`scripts/setup-signing.py`** — auto-creates the *Developer ID Application*
  certificate from an App Store Connect API key, imports it, and fills `signing.env`.
- **`scripts/finish-signing.py`** — finishes setup from a manually issued cert
  (for when the API key isn't the Account Holder and Apple returns 403).
- **Auto-release CI** (`auto-release-dmg.yml`) — pushing a desktop version bump to
  `main` builds the `.dmg` and auto-creates the tag + Release.
- **Signed CI builds** — the GitHub Actions pipeline now signs + notarizes on Apple's
  runners (Apple Developer ID secrets configured), so released `.dmg`s are signed
  whether cut locally or by CI.

### Changed
- `appdist.sh` release notes now state **signed & notarized** when a Developer ID
  identity is configured (previously always "unsigned").
- `appdist.sh` also uploads the updater artifacts (`latest.json`, `AppPreview.app.tar.gz`,
  `.sig`) alongside the `.dmg`, so auto-update stays valid on locally cut releases.

### Notes
- Builds are **Apple Silicon (aarch64)**. Intel/universal builds are not produced yet.
- Auto-update (Tauri updater) ships the `latest.json` manifest with each release, so
  installed apps see new versions via **File ▸ Check for Updates…**.

## 0.1.0 — 2026-06-24

**First release — App Preview.** A local tool to preview and polish your App Store and
Google Play listings before shipping.

### Main features
- **Load live listings** from App Store Connect + Google Play via API keys (⟳ Sync).
- **Preview the new version** (text + screenshots, per locale) before uploading.
- **Review Diff** — Current → New, field-by-field text and slot-by-slot screenshots.
- **First-release checklist** — a gate covering everything a new submission needs.
- **Store SEO / ASO audit** — title/subtitle/keyword limits + tips, per locale.
- **Test keys** — verify ASC + Google Play credentials without saving.
- **Import / Export** — JSON config or a self-contained base64 `.env`.
- **Multi-language** UI + docs (en, vi, ko, ar, ja); runs fully locally.

### Packaging
- macOS desktop build: **Tauri** shell + bundled **Python `serve.py`** sidecar
  (PyInstaller), opening straight into the Playground tool.
- Tauri **auto-updater** wired to the GitHub `latest.json` endpoint.
- Unsigned build (Gatekeeper workaround required) — fixed in 0.2.0.
