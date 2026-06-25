---
title: Changelog
description: Release notes for the App Preview macOS desktop app — signed & notarized .dmg downloads, auto-update, and what changed in each version.
sidebar:
  order: 7
---

Release notes for the **App Preview** macOS desktop app. Each version is published to
[GitHub Releases](https://github.com/fighttechvn/app_marketing/releases) as a
**signed, notarized `.dmg`**, and installed apps **auto-update** themselves.

👉 **[Download the latest .dmg](https://github.com/fighttechvn/app_marketing/releases/latest)**

## 0.2.0 — 2026-06-25

**Signed & notarized builds, auto-update, and one-command deploy.** This is the first
release you can download and open like any normal Mac app — no scary warnings, no
terminal workarounds.

### ✨ Highlights

#### Signed with Developer ID + notarized by Apple

The `.app` and `.dmg` are now code-signed with a **Developer ID Application**
certificate and **notarized by Apple** (with the notarization ticket stapled). Double-
click the `.dmg`, drag to Applications, open — **no "AppPreview is damaged" warning**
and no `xattr -dr com.apple.quarantine` workaround. Verified with:

```
spctl -a -vvv -t exec AppPreview.app   →  accepted, source=Notarized Developer ID
```

#### Auto-update built in

The app keeps itself up to date via the **Tauri updater**:

- **File ▸ Check for Updates…** — plus a silent check on launch — compares against the
  latest GitHub release.
- When a newer version exists it **downloads, verifies, installs, and relaunches** — no
  manual reinstall.
- Updates are **cryptographically signed** (separate from Apple signing), so the app
  only installs builds published by us.

#### One-command release (`deploy.sh`)

Shipping a build is now a single command. `deploy.sh`:

1. ensures the private signing assets are present (clones them if missing),
2. imports the Developer ID certificate into the keychain,
3. builds, signs, **notarizes**, and **publishes** the `.dmg` + updater manifest to a
   GitHub Release.

#### Signed builds in CI

The GitHub Actions pipeline (`release-dmg.yml` / `auto-release-dmg.yml`) now builds
**signed + notarized** `.dmg`s on Apple's runners. Bump the version on `main` and the
release — `.dmg`, updater bundle, and `latest.json` — is cut automatically.

### Added
- Developer ID code-signing + Apple notarization of the `.app` and `.dmg`.
- Auto-update manifest (`latest.json`) published with every release.
- `deploy.sh` — ensure signing assets → build → sign → notarize → publish.
- `setup-signing.py` — auto-create the Developer ID certificate from an App Store
  Connect API key.
- `finish-signing.py` — finish signing from a manually issued certificate.

### Changed
- Release notes now state **signed & notarized** when a Developer ID identity is set.
- `appdist.sh` uploads the updater artifacts (`latest.json`, `.app.tar.gz`, `.sig`)
  alongside the `.dmg`, so auto-update stays valid on locally cut releases.

### Notes
- Builds are **Apple Silicon (aarch64)**. Intel / universal builds aren't produced yet.

See the [desktop app guide](/app_marketing/docs/guides/desktop-app/) for build and
signing details.

## 0.1.0 — 2026-06-24

- Initial macOS desktop build: a **Tauri** shell wrapping the Playground tool with a
  bundled **Python sidecar** (PyInstaller), opening straight into the tool.
- Tauri **auto-updater** wired to the GitHub release manifest.
- ⚠️ Unsigned — required a Gatekeeper workaround to open. Fixed in 0.2.0.
