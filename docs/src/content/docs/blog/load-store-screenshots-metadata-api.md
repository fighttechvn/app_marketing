---
title: Load store screenshots & metadata via App Store & Play API
date: 2026-06-24
authors: fighttech
excerpt: Pull live screenshots and metadata text from App Store Connect and Google Play with your API keys — straight into the store-preview tool. Here's how it works.
tags: [app-store, google-play, api, screenshots]
---

**Loading store screenshots and metadata** by hand is slow and error-prone. The
store-preview tool pulls them straight from **App Store Connect** and **Google
Play** using your API keys, so the Current variant always mirrors what is live.

## What gets loaded

One **Sync** click reads, per store:

- **App Store Connect** — iPhone and iPad screenshots plus the localized name,
  subtitle, keywords, promotional text, description, and "what's new".
- **Google Play** — phone screenshots plus the title, short description, and full
  description for every locale.

Screenshots are downloaded into `assets/current/` and the text is written to
`listing-current.json`, so the **Current** variant reflects the live listing
exactly.

## How the API access works

The tool authenticates the same way the official tooling does:

- App Store Connect uses a **JWT signed with your `.p8` API key** (key id + issuer id).
- Google Play uses a **service-account JSON** with the Android Publisher scope.

You only set these once. See the [environment variables reference](/reference/env-variables/)
for every key, and [Get your store API keys](/guides/api-keys/) for step-by-step
instructions on creating them.

## Try it

Open the [Playground](/playground/), add your keys via **Import → Env**, click
**🔌 Test keys** to confirm access, then **⟳ Sync**. Within seconds the Current
variant shows your live App Store and Google Play listing — ready to
[diff against your new version](/guides/usage/).
