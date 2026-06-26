---
title: First-release checklist for App Store & Google Play
date: 2026-06-24
authors: fighttech
excerpt: Ship your first app with confidence — a complete checklist covering the screenshots, metadata, and graphics required for App Store and Google Play, plus the full step-by-step deploy flow for iOS (App Store Connect + Xcode) and Android (Play Console + AAB).
tags: [app-store, google-play, checklist, release, ios, android, deploy]
---

A **first-release checklist for the App Store and Google Play** is the difference
between a smooth launch and a rejection email. A brand-new app has the strictest
requirements, and they're easy to miss when you're focused on the build. This
guide covers two things: the **listing checklist** (what every store needs), and
the **end-to-end deploy flow** for each store — from account to "Available".

## What the checklist covers

Open **Release checklist** in the tool to verify, before you submit:

- **Screenshots** — present for every required device size (iPhone 6.9", iPad 13",
  Android phone) with the correct dimensions and no alpha channel.
- **Metadata** — name, subtitle/short description, keywords, and full description
  filled for every locale you ship.
- **Graphics** — app icon (1024×1024 / 512×512) and Google Play feature graphic
  (1024×500).
- **Policy items** — privacy, content rating, and category set.

## Why a first release is different

For an app already on the stores, most fields carry over. A **first release**
starts empty, so the checklist acts as a final gate — confirming each store has
everything it needs before you hit submit. Two things also exist *only* on a
first submission: setting up **signing/distribution** and getting through the
**stricter first-time review**. The deploy steps below cover both.

---

## Deploy to the App Store (iOS)

### 0. Prerequisites

- **Apple Developer Program** membership (US$99/year) — enroll at
  [developer.apple.com](https://developer.apple.com/programs/).
- **Xcode** on a Mac (latest stable), signed in with your Apple ID under
  *Settings → Accounts*.
- A unique **Bundle ID** (e.g. `com.yourcompany.yourapp`).

### 1. Create the app record in App Store Connect

1. Go to [App Store Connect](https://appstoreconnect.apple.com/) → **My Apps → +
   → New App**.
2. Pick the platform (iOS), **name**, **primary language**, **Bundle ID**, and a
   **SKU** (any internal id).
3. Set **Pricing and Availability** (free/paid, territories).

### 2. Sign and upload the build

1. In Xcode, set the **Version** (e.g. `1.0.0`) and **Build** number.
2. Enable **Automatically manage signing** (Xcode creates the distribution
   certificate + provisioning profile), or manage them manually in
   *Certificates, Identifiers & Profiles*.
3. Select **Any iOS Device (arm64)** → **Product → Archive**.
4. In the **Organizer**, choose the archive → **Distribute App → App Store
   Connect → Upload**. (Alternatively, export the `.ipa` and upload with the
   **Transporter** app.)
5. Wait for **build processing** to finish in App Store Connect (a few minutes to
   an hour) before the build can be attached to a version.

### 3. Fill the version listing

On the app's **1.0 Prepare for Submission** page:

- **Screenshots** — upload per device size (6.9" iPhone is required; iPad 13" if
  you support iPad). Prep them in the [Playground](/playground/).
- **Promotional text, description, keywords, support URL, marketing URL.**
- **App icon** is taken from the uploaded build (1024×1024, no alpha).
- **App Privacy** — complete the data-collection questionnaire (required).
- **Age Rating** questionnaire, **Category**, and **Pricing**.
- Select the processed **Build** from step 2.

### 4. (Optional) TestFlight beta

Add internal/external testers under **TestFlight** to validate the exact build
before public review. External testers require a quick beta review.

### 5. Submit for review → release

1. Choose how to release: **Automatically**, **Manually**, or **Phased release**
   (gradual rollout to existing users — for first release it controls the ramp).
2. Click **Add for Review → Submit**.
3. First-time reviews are stricter and can take from a few hours to a couple of
   days. Watch for **Metadata Rejected** vs **Binary Rejected** — the former you
   fix in the listing, the latter needs a new build.
4. On approval, the app goes **Pending Developer Release** (manual) or live
   automatically.

---

## Deploy to Google Play (Android)

### 0. Prerequisites

- **Google Play Developer account** (one-time US$25) — register at the
  [Play Console](https://play.google.com/console/).
- **Android Studio** to build a signed **Android App Bundle (`.aab`)** — Play
  requires AAB, not APK, for new apps.
- A **privacy policy URL** (required for essentially every app now).

### 1. Create the app in the Play Console

**All apps → Create app** → set the **app name**, default language, **App or
Game**, **Free or Paid**, and accept the declarations.

### 2. Set up signing (Play App Signing)

1. Build a signed **release AAB**: Android Studio → **Build → Generate Signed
   Bundle / APK → Android App Bundle**, using your **upload keystore** (keep it
   safe — losing it means a recovery process).
2. **Play App Signing** is on by default: you sign with the *upload key*, Google
   re-signs with the *app signing key* it manages. This is what end users get.

### 3. Complete the store listing & policy declarations

Under **Grow → Store presence → Main store listing** and the **Policy / Dashboard**
tasks:

- **Short description** (≤80 chars) and **full description** (≤4000).
- **Screenshots** (min 2 per form factor), **app icon** (512×512), and the
  **feature graphic** (1024×500) — prep these in the [Playground](/playground/).
- **Content rating** questionnaire (IARC).
- **Target audience & content**, **Data safety** form, **Ads** declaration,
  **App access** (login details if anything is gated), and **Privacy policy** URL.
- **Category** and contact details.

### 4. Create a release on a track

Releases roll out through tracks — promote upward as confidence grows:

**Internal testing** → **Closed testing** → **Open testing** → **Production**.

1. **Release → (track) → Create new release**.
2. Upload the **AAB**, set the **release name** and **release notes**.
3. New personal-developer accounts may need a period of **closed testing with N
   testers** before Production is unlocked — check the console's requirements.

### 5. Roll out & review

1. **Review release → Start rollout to Production**.
2. Use **staged rollout** (e.g. 10% → 50% → 100%) to limit blast radius.
3. First-app review typically takes from a few hours up to ~7 days. Once approved
   and rolled out, the listing goes live (propagation can take a few hours).

---

## Prep your listing assets first

Both stores reject on the same avoidable things: wrong screenshot sizes, an icon
with an alpha channel, a description that overflows, or a missing localized field.
Build your **New** version in the [Playground](/playground/), run the
[first-release checklist](/guides/usage/#first-release-checklist), and fix anything
flagged. Pair it with the [store SEO audit](/guides/usage/#store-seo-audit-aso) so
your launch listing is both **complete** and **discoverable**.

To pull credentials and live data for **Sync** / **Test keys**, see
[Get your API keys](/guides/api-keys/).
