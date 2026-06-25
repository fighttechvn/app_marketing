# EP02: Store Sync User Stories

Feature: pull the live listing (metadata + screenshots) from App Store Connect and Google Play into the **Current** variant (`GET /api/sync` → `stores.py`).

## EP02.US001: Sync the live App Store listing
As a developer, I want to pull my current App Store listing so that I can diff and preview against what users see today.

Acceptance criteria:
- ⟳ Sync authenticates to App Store Connect with a JWT minted from `ASC_KEY_ID` / `ASC_ISSUER_ID` / the `.p8` key (ES256, ~1100 s expiry).
- The app is resolved by `BUNDLE_ID`; the latest `appStoreVersion` and per-locale `appStoreVersionLocalization` fields (name, subtitle, keywords, promotionalText, description, whatsNew) are fetched.
- iPhone (`APP_IPHONE_67`) and iPad (`APP_IPAD_PRO_3GEN_129`) screenshots are downloaded to `assets/current/` and labeled with their original dimensions.
- Results are written to `listing-current.json`.

## EP02.US002: Sync the live Google Play listing
As a developer, I want to pull my current Play listing so that the Current variant reflects production.

Acceptance criteria:
- Sync authenticates with the Play service account JSON over the `androidpublisher` scope and opens an edit session.
- All `listings` languages are fetched (title, shortDescription, fullDescription).
- `phoneScreenshots` for en-US are downloaded to `assets/current/`.
- The edit session is discarded (read-only; no store changes).

## EP02.US003: See a clear sync result
As a user, I want feedback after syncing so that I know what was loaded.

Acceptance criteria:
- A toast reports counts, e.g. "Synced — App Store iPhone 3 / iPad 2, Play phone 5 (v1.4.0)".
- `GET /api/sync` returns `{ok, appstore:{iphone,ipad}, googleplay:{phone}, locales[], versionName}`.
- Missing/invalid credentials produce a readable error, not a crash; preview-only use (no keys) still works.

## EP02.US004: Keep credentials on the machine
As a security-conscious user, I want sync to run locally so that my keys never leave my device.

Acceptance criteria:
- The server binds `127.0.0.1` only.
- Credentials load from `{project}/.env` and optionally `{APP_DIST}/.env.prod`; nothing is uploaded to a third party.
