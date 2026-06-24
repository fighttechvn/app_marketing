---
title: Preview your store listing before you ship
date: 2026-06-24
excerpt: Why we built a local store-listing preview — sync live data, diff New vs Current, and verify keys before uploading anything.
tags: [release, tooling]
---

Shipping a mobile update means juggling two pictures of your store listing: what's
**live now**, and what you're **about to upload**. It's easy to upload the wrong
screenshot order, forget a localized description, or push a key that turns out to
be missing a permission.

The store-preview tool puts both pictures side by side, locally, before anything
leaves your machine:

- **New** is what you're about to submit — fill it from a template, from *Load
  images*, or drag & drop.
- **Current** is what's live — pulled straight from App Store Connect and Google
  Play with one **Sync** click.
- **Review Diff** shows exactly what changed, text and screenshots, per locale.

And because credentials are the usual pain point, there's a **Test keys** button
that verifies your App Store Connect key and Play service account against the live
APIs *before* you save them.

Start with the [setup guide](/guides/setup/), then wire up your
[environment variables](/reference/env-variables/).
