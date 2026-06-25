# Credentials Import / Export

## Layout Mode: Tab-based modal (Export & Import)

```
┌──────────────────────────────────────────────────────────────┐
│ Export config                                          [✕]   │
├──────────────────────────────────────────────────────────────┤
│ [ Listing JSON ] [ Env · Sync API ]                          │
├──────────────────────────────────────────────────────────────┤
│ ⚠️ CONTAINS REAL CREDENTIALS — keep private                  │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ASC_KEY_ID=...                                           │ │
│ │ ASC_ISSUER_ID=...                                        │ │
│ │ ASC_KEY_P8_B64=...                                       │ │
│ │ BUNDLE_ID=...                                            │ │
│ │ PLAYSTORE_PACKAGE_NAME=...                               │ │
│ │ PLAYSTORE_SERVICE_ACCOUNT_JSON_B64=...                   │ │
│ └──────────────────────────────────────────────────────────┘ │
│              [ 💾 Save .env ]  [ 🔌 Test keys ]              │
├──────────────────────────────────────────────────────────────┤
│ Test result:  ✓ App Store Connect: app found                 │
│               ✓ Google Play: sa@project.iam … edit ok        │
└──────────────────────────────────────────────────────────────┘
```

## Components
- Tabs: Listing JSON (copy / save .json) · Env · Sync API.
- Env textarea: editable on Import, read-only export shows current server env.
- Buttons: Save .env (POST /api/env), Test keys (POST /api/test), Copy, Choose file, Load → Current.
- Result area: per-store ✓ (green) / ✗ (red) + detail.

## States
- Export: prefilled from `GET /api/env` (sync keys only, base64-inlined).
- Import: paste/pick; Save refuses overwrite unless `?force=1`.
- Tested: per-store ok/detail rendered.

## Events
- TestKeys → POST /api/test → render results.
- SaveEnv → POST /api/env.
- LoadToCurrent → set parsed JSON as read-only Current.

## SRS Export
- `resources/srs.sh` renders this document inside `Screens / UI Surfaces`.
