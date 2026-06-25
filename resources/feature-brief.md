# App Preview — Product Feature Brief

## Product
- **Name:** App Preview (Store Listing Preview)
- **Tagline:** Preview, diff, and QA your App Store / Google Play listing before you ship.
- **Primary user:** Mobile app developers, indie publishers, and release managers preparing a first submission or a version update.
- **Platforms:** Local web app (one origin via `run.sh`), static GitHub Pages build (preview-only), and a signed macOS / Windows desktop app (Tauri shell + bundled Python sidecar).
- **Repository:** `fighttechvn/app_marketing` · Live docs: https://fighttechvn.github.io/app_marketing/

## Problem
App stores only show you how a listing looks **after** you upload it. There is no safe sandbox to:
- See exactly how a *new* version of a listing renders on iPhone, iPad, and Android phone/tablet.
- Compare the new listing against what is *currently live* on the store.
- Catch ASO / character-limit problems and missing first-release assets *before* submission.
- Verify App Store Connect and Google Play API credentials without risking a bad write.

App Preview closes that gap with a local, credentials-stay-on-device tool.

## Epic catalog
| Epic | Feature | Slug |
|---|---|---|
| EP01 | Store Listing Preview (Playground) | `ep01-store-preview` |
| EP02 | Store Sync (App Store Connect + Google Play) | `ep02-store-sync` |
| EP03 | Review Diff (Current → New) | `ep03-review-diff` |
| EP04 | Store SEO / ASO Audit | `ep04-aso-audit` |
| EP05 | First-Release Checklist | `ep05-release-checklist` |
| EP06 | Credentials, Import/Export & Key Verification | `ep06-credentials` |
| EP07 | Device Mirror & Remote Control | `ep07-device-mirror` |
| EP08 | Desktop App Distribution | `ep08-desktop-app` |

## Scope
- **In scope:** Listing preview/edit, live store sync (read), diffing, ASO audit, release checklist, credential test/import/export, live device mirroring, desktop packaging + auto-update.
- **Out of scope:** *Writing/uploading* metadata or screenshots back to the stores (the tool is read + preview + export; the actual upload happens in App Store Connect / Play Console). Build signing for the *user's* app, payments, analytics.
- **Assumptions:** User holds (or can create) ASC API key + Play service account. macOS for iOS sync/mirroring and desktop signing. Backend runs on `127.0.0.1` only.

## Architecture at a glance
- **Frontend:** `index.html` (~117 KB single-file Playground, vanilla JS) + `home.html` (landing).
- **Backend:** `serve.py` shim → `server/` package (`http_app.py` routing, `stores.py` ASC/Play, `android.py`, `ios.py`, `preview.py`, `project.py`, `credentials.py`, `context.py`, `util.py`, `envfile.py`).
- **Docs:** Astro Starlight under `docs/` → `docs/dist/`.
- **Desktop:** `desktop/` Tauri app (`src-tauri/`) + PyInstaller sidecar of the backend.

## Documentation outputs
- User stories: `resources/user-story/epXX-*.md`
- Technical design: `resources/technial-design/epXX-*.md`
- Screen layouts (ASCII): `resources/screens/epXX-*-screen.md`
- Master SRS: `resources/srs.md` → rendered to `srs-index.html` by `resources/srs.sh`
