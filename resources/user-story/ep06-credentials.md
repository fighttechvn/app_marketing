# EP06: Credentials, Import/Export & Key Verification User Stories

Feature: import/export of listing JSON and `.env`, plus non-destructive credential verification (`POST /api/test`, `GET`/`POST /api/env`).

## EP06.US001: Verify API keys without saving
As a developer, I want to test my App Store Connect and Google Play credentials so that I know they work before I rely on them.

Acceptance criteria:
- "Test keys" POSTs the pasted `.env` to `/api/test`; nothing is written to disk.
- App Store test mints a JWT and calls `/v1/apps?filter[bundleId]=…`; result reports ok + detail.
- Google Play test authenticates the service account and opens then deletes a throwaway edit; result reports ok + the service-account email.
- Each store shows ✓ (green) or ✗ (red) with a readable detail message.

## EP06.US002: Import a listing or credentials
As a user, I want to import a listing JSON or `.env` so that I can load a config from elsewhere.

Acceptance criteria:
- Import offers two tabs: Listing JSON and Env · Sync API.
- Listing JSON: paste or pick a `.json` file → "Load → Current" sets it as the read-only Current variant.
- Env: paste or pick a file → "Save .env to local" POSTs to `/api/env`; by default it does not overwrite an existing `.env` (requires `?force=1`).

## EP06.US003: Export a self-contained config
As a user, I want to export my listing and a self-contained `.env` so that I can hand off or back up my setup.

Acceptance criteria:
- Export offers Listing JSON (copy / save `.json`) and Env · Sync API.
- The exported `.env` includes only SYNC keys (ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8 → `_B64`, BUNDLE_ID, PLAYSTORE_PACKAGE_NAME, PLAYSTORE_SERVICE_ACCOUNT_JSON → `_B64`); signing/Firebase secrets are never exported.
- File-path credentials are base64-inlined so the `.env` is self-contained (no side files).
- The export warns that it contains real credentials and must be kept private.
