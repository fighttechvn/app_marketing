# Changelog

All notable changes to the **App Preview** macOS desktop app. Releases are tagged
`desktop-v<version>` and published to
[GitHub Releases](https://github.com/fighttechvn/app_marketing/releases).

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

### Changed
- `appdist.sh` release notes now state **signed & notarized** when a Developer ID
  identity is configured (previously always "unsigned").

### Notes
- Builds are **Apple Silicon (aarch64)**. Intel/universal builds are not produced yet.
- Auto-update (Tauri updater) ships the `latest.json` manifest with each release, so
  installed apps see new versions via **File ▸ Check for Updates…**.

## 0.1.0 — 2026-06-24

- Initial macOS desktop build: **Tauri** shell + bundled **Python `serve.py`**
  sidecar (PyInstaller), opening straight into the Playground tool.
- Tauri **auto-updater** wired to the GitHub `latest.json` endpoint.
