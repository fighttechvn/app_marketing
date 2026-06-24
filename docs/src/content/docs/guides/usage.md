---
title: Usage
description: Try template, Sync, Review Diff, Import/Export and Test keys.
sidebar:
  order: 3
---

## Try template (fill New)

New starts empty. Click **✨ Try template** to copy the bundled demo
(`assets/template/` → `assets/new/`) into the New variant and rewrite
`listing.json` to point at it. Then replace the screenshots/text with your own.

> The button only appears when a `listing-template.json` is bundled (the template
> repo). It is hidden on a real listing.

## Sync (fill Current)

Click **⟳ Sync** to pull the live listing from App Store Connect (iPhone/iPad
screenshots + metadata) and Google Play (phone screenshots + metadata). It writes
`listing-current.json` and downloads images into `assets/current/`, then reloads
the Current variant. Requires credentials.

## Review Diff

Click **Review Diff** to compare **Current → New** in a dialog with two tabs:

- **Text & metadata** — per-locale field changes (name, subtitle, description, …).
- **Screenshots** — slot-by-slot visual comparison; click an image for a fullscreen
  lightbox.

If Current hasn't been synced, every New screenshot shows as **added**.

## Import / Export

- **⤓ Export** → dump the current config as JSON, or an `.env` for the Sync API.
  The `.env` embeds the `.p8` and service-account JSON as **single-line base64**
  (`ASC_KEY_P8_B64`, `PLAYSTORE_SERVICE_ACCOUNT_JSON_B64`) so it is self-contained.
- **⤒ Import** → paste or pick a config JSON, or paste an `.env`. On first import
  the `.env` is saved to local (won't clobber an existing one).

## First-release checklist

Click **Release checklist** to open a checklist that covers everything a first
store submission needs — screenshots for each required device size, metadata
fields filled for every locale, graphics (icon / feature graphic), and store
policy items. Use it as a final gate before you submit a brand-new app.

## Store SEO audit (ASO)

Toggle **ASO checks** to audit the listing for mobile store SEO: it flags
title / subtitle / keyword length against each store's limits, highlights empty
or over-long fields, and surfaces tips to improve discoverability — per locale,
for both the App Store and Google Play.

## Test keys

In **Import → Env**, paste your `.env` and click **🔌 Test keys**. The server
verifies, **without saving**:

- **App Store Connect** — builds a JWT and looks up the app by bundle id.
- **Google Play** — opens & deletes a throwaway edit to confirm app access.

You get a ✓/✗ line per store with details (app name / service-account email /
error). Recommended flow: **paste → Test keys → Save .env → Sync**.
