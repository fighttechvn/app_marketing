---
title: How to get each .env variable
description: A per-variable walkthrough — what each .env value is, exactly where to obtain it, and how to put it in your .env (path or single-line base64).
sidebar:
  order: 2
---

This page explains, **variable by variable**, where each `.env` value comes from
and how to set it. For the at-a-glance table see the
[environment variables reference](/reference/env-variables/); for creating the keys
step-by-step see [Get your API keys](/guides/api-keys/).

You only need these for **Sync** and **Test keys**. The preview, New/Current toggle,
Try template and Review Diff need nothing.

## Server

### `PORT`
The local port the preview server listens on (default `8092`). Pick any free port —
e.g. `PORT=8092`.

### `APP_DIST`
Path to the repo that holds your fastlane metadata + credentials (default
`../../.app_dist`). Only set this if you keep keys in a separate repo.

## App Store Connect (iOS)

### `BUNDLE_ID`
Your iOS bundle id, e.g. `vn.fighttech.go2048`.
**Where:** App Store Connect → your app → **General → App Information → Bundle ID**.

### `ASC_ISSUER_ID`
One issuer id per team (a UUID).
**Where:** App Store Connect → **Users and Access → Integrations → App Store Connect
API** → shown at the top as **Issuer ID**. Copy it verbatim.

### `ASC_KEY_ID`
The id of a specific API key (10 chars, e.g. `5F4KKWDHNV`).
**Where:** same Keys page → the **Key ID** column of the key row.

### `ASC_KEY_P8` *or* `ASC_KEY_P8_B64`
The private key. You need the **Admin** or **App Manager** role to create one.
**Where:** click **Generate API Key**, name it, choose access **App Manager**, then
**download `AuthKey_<KEYID>.p8`** — it downloads **only once**.

Put it in `.env` one of two ways:

```ini
# A) path to the file
ASC_KEY_P8="./AuthKey_5F4KKWDHNV.p8"
```
```sh
# B) embed as single-line base64 (preferred — self-contained .env)
ASC_KEY_P8_B64="$(base64 -i AuthKey_5F4KKWDHNV.p8)"
```

## Google Play (Android)

### `PLAYSTORE_PACKAGE_NAME`
Your Android package name, e.g. `vn.fighttech.go2048`.
**Where:** Google Play Console → your app (top of the dashboard).

### `PLAYSTORE_SERVICE_ACCOUNT_JSON` *or* `..._B64`
A Google service-account key with access to your Play app.
**Where:**
1. **Google Cloud Console → IAM & Admin → Service Accounts** → create one in the
   project linked to Play.
2. **Keys → Add key → Create new key → JSON** → download `sa.json`.
3. **Play Console → Users and permissions → Invite new users** → invite the
   service-account email and grant your app's release + listing permissions.

```ini
# A) path
PLAYSTORE_SERVICE_ACCOUNT_JSON="./sa.json"
```
```sh
# B) embed as single-line base64
PLAYSTORE_SERVICE_ACCOUNT_JSON_B64="$(base64 -i sa.json)"
```

## Path or base64?

| | Path (`ASC_KEY_P8`, `..._JSON`) | Base64 (`ASC_KEY_P8_B64`, `..._JSON_B64`) |
| --- | --- | --- |
| Stored as | a file beside `.env` | a single line inside `.env` |
| Portable to another machine | copy 2 files | copy **only** `.env` ✅ |
| Used by | local dev | Export ▸ Env / desktop app |

The tool's **Export ▸ Env** always emits the base64 form, so the `.env` is fully
self-contained.

## Verify before relying on them

Open the [Playground](/playground/) → **Import → Env**, paste your `.env`, click
**🔌 Test keys**. The tool authenticates against both stores **without saving** and
shows ✓/✗ per store. A common failure is **App Store 401** — that means the
`ASC_KEY_ID` / `ASC_ISSUER_ID` / `.p8` don't match a valid key (check for
placeholders or a truncated base64). Once green, **Save .env** then **Sync**.

:::caution
A filled `.env` holds **real credentials** — keep it private, never commit or share
it, and rotate the keys if a copy leaks.
:::
