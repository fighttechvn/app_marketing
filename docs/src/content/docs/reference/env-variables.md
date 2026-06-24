---
title: Environment variables
description: Every variable the Sync / Test features need, and exactly how to obtain each one.
sidebar:
  order: 1
---

These are the only variables the live features read (the tool's `SYNC_KEYS`
allow-list). **Signing, keystore, and Firebase secrets are never exported** —
they stay server-side.

## Quick reference

| Variable | Required | What it is | How to get it |
| --- | --- | --- | --- |
| `PORT` | – | Server port (default `8092`) | Pick any free port |
| `APP_DIST` | – | Path to the repo holding metadata/creds (default `../../.app_dist`) | Your own private repo |
| `BUNDLE_ID` | iOS | iOS bundle id, e.g. `vn.fighttech.go2048` | App Store Connect → your app → **General → Bundle ID** |
| `ASC_KEY_ID` | iOS | App Store Connect API **Key ID** | ASC → **Users and Access → Integrations → App Store Connect API → Keys** (the *Key ID* column) |
| `ASC_ISSUER_ID` | iOS | Issuer ID (one per team) | Same Keys page, shown at the top as **Issuer ID** |
| `ASC_KEY_P8` *or* `ASC_KEY_P8_B64` | iOS | The `.p8` private key — as a **file path**, or **single-line base64** | **Generate API Key** (role Admin / App Manager) and download `AuthKey_XXXX.p8` (**downloadable once**). Base64: `base64 -i AuthKey_XXXX.p8` |
| `PLAYSTORE_PACKAGE_NAME` | Android | Android package name | Google Play Console → your app |
| `PLAYSTORE_SERVICE_ACCOUNT_JSON` *or* `..._B64` | Android | Service-account JSON — **path** or **single-line base64** | See [Google Play service account](#google-play-service-account) below |

## App Store Connect API key

1. Go to **App Store Connect → Users and Access → Integrations → App Store Connect API**.
2. You need the **Admin** or **App Manager** role to create keys.
3. Note the **Issuer ID** (top of the page) → `ASC_ISSUER_ID`.
4. Click **Generate API Key** (or the **+**), give it a name, choose access **App Manager**.
5. Copy the new row's **Key ID** → `ASC_KEY_ID`.
6. **Download** the `AuthKey_<KEYID>.p8` file — *you can only download it once*. Store it safely.
7. Use it as a path (`ASC_KEY_P8`) or embed it: `ASC_KEY_P8_B64="$(base64 -i AuthKey_XXXX.p8)"`.

## Google Play service account

1. In **Google Cloud Console → IAM & Admin → Service Accounts**, create a service account (or reuse one) in the project linked to your Play account.
2. Open the account → **Keys → Add key → Create new key → JSON** → download `sa.json`.
3. In **Google Play Console → Users and permissions → Invite new users**, invite the service-account email (`...@...iam.gserviceaccount.com`) and grant it access to the app (release + listing permissions).
4. Use it as a path (`PLAYSTORE_SERVICE_ACCOUNT_JSON`) or embed it: `PLAYSTORE_SERVICE_ACCOUNT_JSON_B64="$(base64 -i sa.json)"`.

:::caution
A `.env` exported from a configured host contains **real credentials**. Keep it
private — never commit or share it. Prefer the `*_B64` form so the file is
self-contained, and verify with **Test keys** before saving.
:::

## Example `.env`

```ini
PORT=8092

# App Store Connect (iOS: iPhone/iPad screenshots + metadata)
ASC_KEY_ID="5XXXXXXXXX"
ASC_ISSUER_ID="2e641cf7-0000-0000-0000-000000000000"
ASC_KEY_P8_B64="LS0tLS1CRUdJTiBQUk...single-line-base64...LS0tLS0="
BUNDLE_ID="vn.fighttech.go2048"

# Google Play (Android: phone screenshots + metadata)
PLAYSTORE_PACKAGE_NAME="vn.fighttech.go2048"
PLAYSTORE_SERVICE_ACCOUNT_JSON_B64="ewogICJ0eXBlIjog...single-line-base64...fQo="
```
