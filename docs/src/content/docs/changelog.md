---
title: Changelog
description: Release notes for the App Preview macOS desktop app — signed & notarized .dmg downloads, auto-update, and what changed in each version.
sidebar:
  order: 7
---

Release notes for the **App Preview** macOS desktop app. Each version is published to
[GitHub Releases](https://github.com/fighttechvn/app_marketing/releases) as a signed,
notarized `.dmg`. Installed apps also auto-update via **File ▸ Check for Updates…**.

👉 **[Download the latest .dmg](https://github.com/fighttechvn/app_marketing/releases/latest)**

## 0.2.0 — 2026-06-25

**Signed & notarized builds + one-command deploy.**

The `.dmg` is now **signed with a Developer ID certificate and notarized by Apple**, so
it opens on any Mac with **no Gatekeeper "AppPreview is damaged" warning** — no more
`xattr` workaround needed.

**Added**

- **Developer ID signing + Apple notarization** of the `.app` and `.dmg`.
- **`deploy.sh`** — one command to ensure signing assets, build, sign, notarize, and
  publish the release.
- **`setup-signing.py`** — auto-creates the *Developer ID Application* certificate from
  an App Store Connect API key.
- **`finish-signing.py`** — completes signing from a manually issued certificate.
- **Auto-release CI** — a desktop version bump on `main` builds and releases the `.dmg`.

**Changed**

- Release notes now state *signed & notarized* when a Developer ID identity is present.

**Notes**

- Builds are **Apple Silicon (aarch64)**; Intel/universal builds aren't produced yet.

See the [desktop app guide](/app_marketing/docs/guides/desktop-app/) for build and
signing details.

## 0.1.0 — 2026-06-24

- Initial macOS desktop build: a **Tauri** shell wrapping the Playground tool with a
  bundled **Python sidecar**, opening straight into the tool.
- Tauri **auto-updater** wired to the GitHub release manifest.
