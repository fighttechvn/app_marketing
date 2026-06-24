---
title: Get your App Store & Google Play API keys
description: Step-by-step guide to create every store API key the tool needs — ASC key id, issuer id, .p8, and the Google Play service-account JSON — and add them to .env.
sidebar:
  order: 2
---

This guide walks through creating **every App Store and Google Play API key** the
tool needs for Sync and Test, then dropping them into `.env`. For the at-a-glance
table, see the [environment variables reference](/reference/env-variables/).

## What you'll create

| Key | Store | Used for |
| --- | --- | --- |
| `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_KEY_P8` | App Store | JWT auth to App Store Connect |
| `BUNDLE_ID` | App Store | Find your app by bundle id |
| `PLAYSTORE_SERVICE_ACCOUNT_JSON` | Google Play | Service-account auth |
| `PLAYSTORE_PACKAGE_NAME` | Google Play | Identify the Play app |

## 1. App Store Connect API key

1. Open **App Store Connect → Users and Access → Integrations → App Store Connect API**.
   You need the **Admin** or **App Manager** role.
2. Copy the **Issuer ID** shown at the top → this is `ASC_ISSUER_ID`.
3. Click **Generate API Key** (the **+**), name it, and choose access **App Manager**.
4. From the new row, copy the **Key ID** → `ASC_KEY_ID`.
5. **Download** the `AuthKey_<KEYID>.p8` file. ⚠️ It can only be downloaded **once** — store it safely.
6. Find your app's **Bundle ID** under your app → **General → Bundle ID** → `BUNDLE_ID`.

### Add it to `.env`

Use the file path:

```ini
ASC_KEY_ID="5XXXXXXXXX"
ASC_ISSUER_ID="2e641cf7-0000-0000-0000-000000000000"
ASC_KEY_P8="./AuthKey_5XXXXXXXXX.p8"
BUNDLE_ID="vn.fighttech.go2048"
```

…or embed the key as single-line base64 so the `.env` is self-contained:

```sh
ASC_KEY_P8_B64="$(base64 -i AuthKey_5XXXXXXXXX.p8)"
```

## 2. Google Play service account

1. In **Google Cloud Console → IAM & Admin → Service Accounts**, create a service
   account in the project linked to your Play account.
2. Open it → **Keys → Add key → Create new key → JSON** → download `sa.json`.
3. In **Google Play Console → Users and permissions → Invite new users**, invite the
   service-account email (`…@…iam.gserviceaccount.com`) and grant it access to your
   app (release + store-listing permissions).
4. Find your **package name** in Play Console → `PLAYSTORE_PACKAGE_NAME`.

### Add it to `.env`

```ini
PLAYSTORE_PACKAGE_NAME="vn.fighttech.go2048"
PLAYSTORE_SERVICE_ACCOUNT_JSON="./sa.json"
```

…or embed it as base64:

```sh
PLAYSTORE_SERVICE_ACCOUNT_JSON_B64="$(base64 -i sa.json)"
```

## 3. Verify before you rely on them

Open the [Playground](/playground/) → **Import → Env**, paste your `.env`, and click
**🔌 Test keys**. The tool authenticates against both stores **without saving** and
reports a ✓/✗ per store. Once green, **Save .env to local** and **Sync**.

:::caution
A populated `.env` holds **real credentials**. Keep it private — never commit or
share it. The `_B64` form keeps everything in one file; rotate the keys if a file
is ever exposed.
:::

## Next steps

- [Load store screenshots & metadata](/blog/load-store-screenshots-metadata-api/)
- [Environment variables reference](/reference/env-variables/)
- [Usage: Sync, Review Diff, Test keys](/guides/usage/)
