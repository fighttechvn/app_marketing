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

## 0.3.0 — 2026-06-25

**Preview panel + real-device mirroring.** The Playground gains a slide-in **preview
panel** (right-side icon rail) for previewing your work and driving real phones without
leaving the tool.

### ✨ Highlights

- **Web / Media / Markdown previews** — load any URL or local path (`/docs/`) in an
  inline frame, open an image / video / audio file, or render a `.md` file — all in a
  slide-in panel.
- **Android mirror + remote control** — live device mirror over `adb`: **click to tap,
  drag to swipe**, keyboard text, and hardware buttons. A `scrcpy ↗` button opens a
  native high-FPS window.
- **iPhone mirror + remote control** — real-device mirror via **WebDriverAgent** over a
  USB tunnel (`iproxy`): live MJPEG stream with tap / swipe / button / text. Clear
  guidance when WDA isn't running on the device.
- **Touch feedback** — a red ripple blooms at each tap; swipes draw a fading trail —
  shared across Android and iPhone.
- All device backends are **localhost-only** (`127.0.0.1`) and resolve `adb` / `scrcpy`
  / `iproxy` even from a GUI-launched app with a minimal `PATH`.

See the [device preview & control reference](/app_marketing/docs/reference/device-preview/)
for the full protocol and architecture.

### Notes
- Android control needs `adb` (Android platform-tools); iPhone control needs
  WebDriverAgent running on the device. Builds remain **Apple Silicon (aarch64)**.

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

**First release — meet App Preview.** A local tool to preview, check, and polish your
**App Store** and **Google Play** listings *before* you ship — see your new version
exactly as users will, side by side with what's live today.

### 🚀 Main features

- **Load live listings from the stores** — pull screenshots + metadata straight from
  **App Store Connect** and **Google Play** with your own API keys, into the *Current*
  variant (⟳ **Sync**). No copy-pasting from the store consoles.
- **Preview your new version** — see exactly how your **New** listing looks on the App
  Store and Google Play before uploading: title, subtitle, description, and screenshots
  — **per locale**.
- **Review Diff (Current → New)** — a side-by-side diff of every change: text/metadata
  field-by-field, and screenshots slot-by-slot with a fullscreen lightbox. Know exactly
  what changed before you submit.
- **First-release checklist** — a built-in gate covering everything a brand-new store
  submission needs: screenshots for each required device size, metadata for every
  locale, icon / feature graphic, and store-policy items.
- **Store SEO audit (ASO)** — flags title / subtitle / keyword lengths against each
  store's limits, highlights empty or over-long fields, and surfaces discoverability
  tips — per locale, for both stores.
- **Test keys** — verify your App Store Connect and Google Play credentials in one click
  (builds a JWT and looks up the app; opens & deletes a throwaway Play edit) — **without
  saving** anything.
- **Import / Export** — move configs as JSON, or as a self-contained `.env` that embeds
  the `.p8` and service-account JSON as single-line base64.
- **Multi-language** — the tool and these docs ship in English, Tiếng Việt, 한국어,
  العربية, and 日本語.
- **Runs locally** — everything stays on your machine; your API keys never leave it.

### 🖥️ Packaging

- Ships as a native **macOS desktop app**: a **Tauri** shell wrapping the tool with a
  bundled **Python sidecar** (PyInstaller), opening straight into the Playground.
- **Auto-update** wired to the GitHub release manifest.
- ⚠️ This build was **unsigned** — it needed a Gatekeeper workaround to open.
  Fixed in [0.2.0](#020--2026-06-25).
