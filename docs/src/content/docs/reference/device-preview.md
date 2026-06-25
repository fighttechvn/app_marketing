---
title: Device preview & control
description: Technical reference for the Playground preview panel — link-triggered Web/Media/Markdown previews plus real Android (adb) and iPhone (WebDriverAgent) mirror & control.
sidebar:
  order: 4
---

The Playground ships a right-side **preview panel** that mirrors and remote-controls
real devices, plus on-demand previews for web pages, media files, and Markdown.
This page documents how it works end to end: the UI module, the `server/` backend
package, the device-control protocols, and the performance characteristics.

> **Localhost only.** Every endpoint below is bound to `127.0.0.1`. The panel shells
> out to `adb`/`scrcpy`/`iproxy`/`xcodebuild` and reads local files, so it must never
> be served on `0.0.0.0` / the LAN.

## At a glance

| Tool | Trigger | Backend | Transport |
|------|---------|---------|-----------|
| 🌐 Web | click a link | — (iframe) | `<iframe>` |
| 🖼️ Media | click a media link | `/api/preview-file` | `<img>`/`<video>`/`<audio>` |
| 📄 Markdown | click a `.md` link | `/api/preview-file` | client-side md→html |
| 📱 Android | rail icon | `/api/adb/*` | `screencap` polling / `scrcpy` |
| 🍎 iPhone | rail icon | `/api/wda/*` | WebDriverAgent MJPEG |

## Architecture

```
index.html  ── preview-panel IIFE (rail, panel, tabs, touch layer)
                 │  fetch()
                 ▼
serve.py  ── thin entry → server/ package
   server/http_app.py   Handler + routing + run()
   server/android.py    adb mirror + control, scrcpy
   server/ios.py        WebDriverAgent mirror + control, xcodebuild launch
   server/preview.py    local-file reader (media + markdown)
   server/stores.py     App Store Connect + Google Play (Sync)
   server/project.py    template / scan / open-folder
   server/context.py    runtime config + mutable ROOT
   server/util.py       find_bin / have / run / download
```

The frontend is a single self-contained IIFE near the end of `index.html`. The
backend was split from a ~830-line `serve.py` into a `server/` package by concern;
`serve.py` is now a thin entry that re-exports `run()` so the existing contracts
still hold (`python3 serve.py [PORT]` and the desktop sidecar's `import serve;
serve.run()`).

### CLI discovery

GUI-launched apps (the Tauri desktop build) inherit a minimal `PATH` that omits the
Android SDK and Homebrew. `util.find_bin(name, env_key)` resolves each tool by, in
order: an explicit `$ENV` override, `PATH`, `$ANDROID_HOME`/`$ANDROID_SDK_ROOT`,
`~/Library/Android/sdk/platform-tools`, and `/opt/homebrew/bin` · `/usr/local/bin` ·
`/usr/bin`. Overrides: `ADB_BIN`, `SCRCPY_BIN`, `IPROXY_BIN`, `GO_IOS_BIN`.

## Preview panel (web / media / markdown)

The Web/Media/Markdown previews are **link-triggered** — they have no always-on rail
buttons and the panel stays hidden until needed. A document-level click handler
intercepts left-clicks on `<a href>`:

- `http(s)://…` → **Web** tab (iframe)
- `…/*.{png,jpg,gif,webp,svg,mp4,webm,mov,mp3,wav,…}` → **Media** tab
- `…/*.{md,markdown,mdx}` → **Markdown** tab (rendered by a small dependency-free
  md→html converter)

Modifier-clicks (`⌘`/`Ctrl`/`Shift`/`Alt`) still open a real new tab; `mailto:`,
`tel:`, `#`, `download`, and links inside the panel are ignored. The opener is also
exposed as `window.ppOpenLink(url)`.

`GET /api/preview-file?path=<abs>` reads a local file and returns it with the right
`Content-Type` (forces `text/markdown` for `.md`/`.markdown`/`.mdx`). Media files
opened from the OS picker use an in-page `blob:` URL instead.

## Android — mirror & control (adb)

### Live mirror

`GET /api/adb/screen?serial=` runs `adb exec-out screencap -p` and streams the raw
PNG (no temp file). The frontend `<img>` re-requests the next frame on each `onload`.

**Performance:** on-device PNG encoding caps `screencap` at roughly **1.5–2 fps**
(~500 ms/frame) regardless of polling cadence. The Android tab shows a live FPS
readout. For a smooth, high-FPS (30–60 fps), low-latency mirror, use the **⚡ scrcpy**
button (`POST /api/adb/scrcpy`), which launches the native scrcpy window.

### Input

`POST /api/adb/input` with a JSON body:

| `action` | Fields | adb command |
|----------|--------|-------------|
| `tap` | `x`, `y` (device **pixels**) | `input tap x y` |
| `swipe` | `x1,y1,x2,y2,ms` | `input swipe …` |
| `text` | `text` | `input text` (spaces → `%s`) |
| `key` | `key` (name) | `input keyevent <code>` |
| `keyevent` | `code` | `input keyevent code` |

Key names map to Android keycodes: `back`, `home`, `recents`, `power`, `volup`,
`voldown`, `enter`, `backspace`, … Click→tap and drag→swipe coordinates are mapped
from the displayed image to **device pixels** using the screenshot's natural size.

`GET /api/adb/devices` lists serials/models and whether scrcpy is running.

## iPhone — mirror & control (WebDriverAgent)

iOS has no `adb` equivalent, so control goes through **WebDriverAgent (WDA)** — the
standard XCUITest agent. `iproxy` (libimobiledevice) forwards WDA's HTTP (`8100`) and
MJPEG (`9100`) ports off-device over USB; the backend talks to WDA's HTTP API and
relays its MJPEG stream.

> **Coordinate space differs from Android.** WDA gestures use logical **points**
> (`window/size`), not screenshot pixels. The frontend maps clicks via the points
> size reported by `/api/wda/status`.

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/wda/devices` | `idevice_id`/`ideviceinfo` device list + `goios`/`tunnel` flags |
| `GET /api/wda/status?udid=` | ensures the tunnel + a WDA session; returns `running` + `size` (points) |
| `GET /api/wda/screen?udid=` | single PNG via WDA `/screenshot` (fallback/snapshot) |
| `GET /api/wda/mjpeg?udid=` | relays WDA's MJPEG stream to the browser `<img>` (live mirror) |
| `POST /api/wda/input` | `tap` / `swipe` / `button` (`home`/`volup`/`voldown`) / `lock` / `text` |
| `POST /api/wda/launch` | one-click WDA launch (see below) |

The live mirror uses WDA's **MJPEG** stream (tuned to ~30 fps, quality 60), which is
smooth in-browser; it falls back to `/screenshot` polling if MJPEG is unavailable.

### Launching WDA (the important part)

On **iOS 17/18**, go-ios `ios runwda` fails to start the test runner
(`pidFromResponse: could not get pid from response`). The reliable path — used by the
**▶ Start WDA** button and `POST /api/wda/launch` — is **`xcodebuild test`** on
Appium's bundled WebDriverAgent project:

```
xcodebuild -project <appium-webdriveragent>/WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner -destination id=<UDID> \
  -allowProvisioningUpdates CODE_SIGNING_ALLOWED=YES \
  DEVELOPMENT_TEAM=<team> test
```

It needs **no sudo tunnel and no go-ios**. The launcher:

1. returns `running:true` immediately if WDA already answers;
2. locates `WebDriverAgent.xcodeproj` (`$WDA_PROJECT` or
   `~/.appium/node_modules/**/appium-webdriveragent/…`);
3. resolves the signing team from `$WDA_TEAM_ID`, else auto-detects it from the
   installed WDA app's `application-identifier`;
4. spawns `xcodebuild test` in the background and returns `launching:true`.

The frontend then polls `/api/wda/status` until WDA answers (first build ~1–3 min,
subsequent ~15 s thanks to cached DerivedData) and auto-connects the mirror. The
**ⓘ Setup** button surfaces the same commands with copy buttons, and
`desktop/scripts/ios-wda-up.sh` does the whole sequence from the terminal.

**Prerequisites:** Xcode, the Appium xcuitest driver (`appium driver install
xcuitest`), and a signing team for WebDriverAgent. The iPhone must be unlocked with
Developer Mode enabled and the developer app trusted.

## Touch feedback

Both device tabs share one `wireMirror()` touch/visual layer. On `pointerdown` a red
ripple blooms at the touch point (instant feedback, before the device round-trip); a
drag draws a fading red trail line with an orange end marker. Taps vs. swipes are
distinguished by distance + duration thresholds.

## Desktop packaging

The Tauri desktop app bundles `serve.py` + `index.html` + the `server/` package into a
PyInstaller sidecar (`desktop/scripts/build-sidecar.sh` stages the package and passes
`--collect-submodules server`). The sidecar seeds a writable data dir and **always
refreshes app-owned files** (`index.html`, `listing-template.json`) on launch so an
app update actually ships the new UI, while preserving user data (`listing.json`,
`assets/`). Rebuild after backend/UI changes with `run_desktop.sh --rebuild-sidecar`.

## Security notes

- All `/api/*` routes bind `127.0.0.1` only — never the LAN.
- `/api/preview-file` reads arbitrary local paths; acceptable for a localhost dev
  tool, but do not expose the server beyond localhost.
- Device control shells out to `adb`/`iproxy`/`xcodebuild`; inputs are passed as
  argument vectors (no shell string interpolation).

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Android mirror ~2 fps | `screencap` PNG limit — use **⚡ scrcpy** for high FPS. |
| "WDA not running" | Click **▶ Start WDA** (runs `xcodebuild`), or launch WebDriverAgentRunner from Xcode. |
| "could not get pid from response" | go-ios can't launch WDA on iOS 18 — the xcodebuild path is used instead. Ensure the iPhone is unlocked, Developer Mode on, app trusted. |
| WDA build fails to sign | Set `WDA_TEAM_ID`, or open `WebDriverAgent.xcodeproj` in Xcode once and pick a team. |
| "WDA screen error" | A second `iproxy 8100` is competing with the server's tunnel — don't run a manual `iproxy 8100` while the server is up. |
| `adb`/`iproxy` not found in desktop app | Set `ADB_BIN`/`IPROXY_BIN`, or ensure `ANDROID_HOME` is exported. |
