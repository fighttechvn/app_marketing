---
title: Generate store screenshots in every size (agent prompts)
description: Copy-paste prompts that drive an AI agent to capture and process App Store and Google Play screenshots in every required size, then drop them into your assets.
sidebar:
  order: 5
---

**Generating store screenshots in every required size** is the most tedious part of
a release. These copy-paste prompts hand the work to an AI coding agent (Claude
Code, etc.): capture from a simulator/emulator, resize to each store's exact spec,
strip the alpha channel, and file them under `assets/`.

## Required sizes

Stores reject the wrong dimensions or any alpha channel, so target these exactly:

| Asset | File name | Size (px) | Notes |
| --- | --- | --- | --- |
| iPhone 6.9" | `iphone-0N.png` | **1320 × 2868** | App Store iPhone |
| iPad 13" | `ipad-0N.png` | **2064 × 2752** | App Store iPad |
| Android phone | `phone-0N.png` | **1344 × 2688** | Play; long side ≤ 2× short side |
| Android tablet | `tablet-0N.png` | **2048 × 2732** (or 16:10) | Play tablet (optional) |
| App icon | `app-icon.png` | **1024 × 1024** (App Store) · **512 × 512** (Play) | **no alpha** |
| Feature graphic | `feature-graphic.png` | **1024 × 500** | Play only |

Drop the results into `assets/new/` (the **New** variant) — or `assets/template/`
to bundle a demo set. See [The integrated site](/guides/the-site/) for the folders.

## Prompt 1 — capture from the iOS Simulator

```text
You are working in a Capacitor/iOS app. Capture App Store screenshots from the
iOS Simulator for these device sizes and save raw PNGs to ./shots-raw/ios/:

- iPhone 6.9" (e.g. "iPhone 16 Pro Max")  → iphone-01..05.png
- iPad 13"  (e.g. "iPad Pro 13-inch (M4)") → ipad-01..05.png

Steps for each device:
1. boot the simulator: `xcrun simctl boot "<device>"`
2. launch the app and navigate to each of the 5 key screens
   (Discover hub, go2048, Zip, Patch, Sudoku)
3. capture: `xcrun simctl io booted screenshot ./shots-raw/ios/<name>-0N.png`

Report the exact pixel size of each captured file when done.
```

## Prompt 2 — capture from the Android emulator

```text
Capture Google Play phone screenshots from a running Android emulator and save
raw PNGs to ./shots-raw/android/ as phone-01..05.png:

1. confirm a device: `adb devices`
2. open the app, navigate to each of the 5 key screens
3. capture: `adb exec-out screencap -p > ./shots-raw/android/phone-0N.png`

Report each file's pixel size. Do not resize yet.
```

## Prompt 3 — process to exact store specs (resize + strip alpha)

```text
Process every raw PNG in ./shots-raw/ into store-ready assets in ./assets/new/.
Stores reject alpha channels and wrong dimensions, so:

- iPhone  → resize/letterbox to exactly 1320x2868, strip alpha
- iPad    → 2064x2752, strip alpha
- Android phone → crop/resize to 1344x2688 (long side must be ≤ 2× short side), strip alpha

Use ffmpeg, scaling to fit then padding (no distortion), forcing RGB (no alpha):

  ffmpeg -y -i in.png \
    -vf "scale=1320:2868:force_original_aspect_ratio=decrease,\
pad=1320:2868:(ow-iw)/2:(oh-ih)/2:white,format=rgb24" \
    -pix_fmt rgb24 assets/new/iphone-01.png

Keep names iphone-0N.png / ipad-0N.png / phone-0N.png. After processing, verify
each output is the exact target size and has NO alpha channel (e.g.
`ffprobe -show_streams` → pix_fmt rgb24). Report a table of file → size → alpha.
```

## Prompt 4 — app icon & Play feature graphic

```text
From the master app icon (./icon-master.png, square, ≥1024px), produce:

- assets/app-icon.png        1024x1024, NO alpha (flatten onto white)
- a 512x512 copy for Google Play
- assets/feature-graphic.png 1024x500 (place the icon + app name on a solid
  brand-color background; no alpha)

Use ffmpeg/ImageMagick, force rgb24 (no transparency). Verify final sizes and
that none has an alpha channel.
```

## Prompt 5 — one-shot, end to end

```text
Produce a complete, store-ready screenshot set for <APP NAME> and place it in
./assets/new/:

1. Capture 5 screens each from the iOS Simulator (iPhone 6.9" + iPad 13") and the
   Android emulator (phone).
2. Resize/letterbox to the exact store specs and STRIP ALPHA:
   iPhone 1320x2868 · iPad 2064x2752 · Android phone 1344x2688.
3. Generate app-icon.png (1024x1024, no alpha) and feature-graphic.png (1024x500).
4. Name files iphone-0N.png / ipad-0N.png / phone-0N.png and put them in
   assets/new/ (icon + feature graphic in assets/).
5. Print a final table: file → dimensions → has-alpha (must all be "no").

Then I will open the Playground, switch to the New variant, and Review Diff.
```

## Verify the result

Open the [Playground](/playground/), make sure you're on the **New** variant — your
screenshots replace the placeholders. Run **Review Diff** against **Current** and the
[first-release checklist](/blog/first-release-checklist-app-store-google-play/) to
confirm every required size is present before you submit.

:::tip
Always end a generation prompt with "report each file's dimensions and whether it
has an alpha channel" — it's the single most common store-rejection cause, and it
makes the agent self-check.
:::
