---
title: "iPhone mirror over AirPlay: setup & troubleshooting (Windows + macOS)"
date: 2026-06-28
excerpt: The 📡 tab mirrors an iPhone wirelessly with a bundled UxPlay + GStreamer — no cable, no Xcode. Here's how it works, plus the issues we hit most on Windows and macOS and how to fix each.
tags: [airplay, desktop, troubleshooting]
---

The **📡 AirPlay** tab mirrors an iPhone's screen straight into the app over Wi‑Fi —
no Lightning cable, no Xcode, no developer trust dance. It runs an embedded
[UxPlay](https://github.com/FDH2/UxPlay) AirPlay receiver, decodes the H.264 mirror
with GStreamer, re‑encodes it to MJPEG on a local port, and shows it in the panel.

It's **view‑only** (AirPlay has no input channel back to the device — for tap/swipe
use the **🍎 iPhone / WDA** tab instead). This post collects the problems that come
up most often and the fix for each, split into a Windows section and a macOS section.

## How it works (30 seconds)

```
iPhone ──AirPlay (Wi-Fi)──▶ UxPlay receiver ──H.264──▶ GStreamer decode
   ▲                                                        │
   └──── discovered via mDNS/Bonjour ──┐        videoconvert ! jpegenc !
                                        │        multipartmux ! tcpserversink
   the app ◀── MJPEG over 127.0.0.1 ◀──┘                    │
   relays it into an <img> in the 📡 panel ◀───────────────┘
```

Everything is bundled: the desktop installer ships `tools/uxplay(.exe)` and a private
copy of GStreamer, so a clean machine needs **nothing** installed. Running from
source falls back to a system UxPlay/GStreamer (or one you pin in **Config ▸ Paths**).

## Quick start

1. Open the **📡** tab → press **▶ Start**.
2. The status flips to **listening…** and the panel shows the receiver name.
3. On the iPhone (same Wi‑Fi): **Control Center → Screen Mirroring →** pick the
   receiver. It's named **`AppPreview - <HOSTNAME>`** so several computers on the
   same network are easy to tell apart.
4. The video appears in the panel. **📸** saves a frame to your screenshots folder
   (drag it into a listing slot); **⤢ Cửa sổ / Window** pops the mirror out larger.

## Issues common to both platforms

- **Same network, please.** The iPhone and the computer must be on the **same
  Wi‑Fi / subnet**. AirPlay is discovered over multicast mDNS, which does not route
  across subnets or VPNs. If your phone is on `192.168.2.x`, the computer has to be too.
- **Black panel until the phone connects.** That's expected — the MJPEG stream only
  carries frames once a device is mirroring.
- **The `connected` flag can lag.** On some setups UxPlay block‑buffers its stdout,
  so the textual "connected" marker shows up late. **The video is the real proof** —
  if you see the screen, it's working, regardless of the flag.
- **Receiver name is ASCII only.** UxPlay rejects a non‑ASCII / non‑UTF‑8 name
  (`detected a non-ascii or non-UTF-8 string …`). The default uses a plain hyphen
  (`AppPreview - HOST`); if you rename it, stick to ASCII.

---

## Windows

### 🔴 The iPhone doesn't see the receiver (no entry in Screen Mirroring)

This is the #1 Windows issue, and it's almost always **mDNS not reaching the phone**,
not the app itself. Work down this list:

1. **Multi‑homed machines / Hyper‑V virtual switches.** If the box runs Hyper‑V,
   WSL2, Docker Desktop, or an Android/phone emulator, it has **several network
   adapters** (e.g. a real LAN plus `Default Switch` on `172.30.x` and assorted
   `vEthernet (...)` switches). UxPlay's built‑in mDNS responder can announce on the
   **wrong interface**, so the phone never hears it. Fix: temporarily **disable the
   virtual switches you aren't using**, leaving only the LAN adapter. In an
   **Administrator** PowerShell:

   ```powershell
   # See what you have (note which one holds your 192.168.x.x address)
   Get-NetIPAddress -AddressFamily IPv4 | Select InterfaceAlias, IPAddress

   # Disable the unused virtual switches (example names — match yours)
   Disable-NetAdapter -Name "vEthernet (Default Switch)" -Confirm:$false
   Disable-NetAdapter -Name "vEthernet (Internal Ethernet Port Windows Phone Emulator Internal Switch)" -Confirm:$false
   ```

   Re‑enable them later with `Enable-NetAdapter`. Restart the receiver (⏹ Stop → ▶ Start)
   after changing adapters.

2. **Windows Firewall.** Allow `uxplay.exe` through (it needs inbound mDNS on UDP
   5353 plus the AirPlay ports). When the firewall is **on**, approve the *Windows
   Security Alert* the first time you Start — be sure to tick **Private networks**.
   If you dismissed it, add a rule manually (Admin):

   ```powershell
   New-NetFirewallRule -DisplayName "UxPlay AirPlay" -Direction Inbound `
     -Program "C:\Path\to\uxplay.exe" -Action Allow -Profile Private
   ```

3. **Router / access‑point isolation.** Some routers enable *AP/client isolation* or
   aggressive *IGMP snooping*, which drops mDNS between the Wi‑Fi and wired segments.
   Test by putting the computer on the **same Wi‑Fi** as the phone; if it shows up
   then, it's the router.

4. **Give it a few seconds** and pull the phone's Control Center down again — iOS
   caches the AirPlay list and sometimes needs a refresh (toggling Wi‑Fi off/on helps).

### 🔴 "uxplay.exe — Entry Point Not Found: `vkCmdPipelineBarrier2`"

A blocking dialog about `libgstvulkan-1.0-0.dll` the moment you press Start. The
bundled GStreamer included the **Vulkan** plugin, which load‑time imports Vulkan 1.3
symbols a machine's older `vulkan-1.dll` may not export. We **don't render with
Vulkan** (the mirror uses the MJPEG sink), so the build now removes the Vulkan
plugin + helper DLL. If you see this, **update to the latest build**; from source,
rebuild the tools (`bash scripts/build-uxplay-gstreamer.sh windows`).

### 🔴 Receiver won't start / exits immediately

- **Non‑ASCII name** — see the shared note above; rename to plain ASCII.
- **A GStreamer plugin fails to load** ("the specified module could not be found").
  Almost always a **missing transitive DLL**. The bundler now ships the **entire**
  GStreamer `bin/` and pulls in extras like `json-glib`; if you trimmed the bundle,
  widen it back.

### 🛠 Building the Windows bundle from source

The bundle is produced under **MSYS2 / UCRT64**. Pitfalls we hit on a clean box:

- **Old MSYS2.** A pre‑2021 install (`msys2-runtime` 3.0.x) has **no `ucrt64` repo**,
  an outdated keyring, and no `zstd`, so `pacman` can't even read today's databases.
  Don't fight it — **install the current MSYS2** and use the **UCRT64** shell.
- **`build_windows` needs four things the stock script didn't have** (all fixed now):
  - `gst-libav` for the software H.264 decoder `avdec_h264` (belt‑and‑suspenders next
    to the d3d11 / openh264 decoders),
  - the **Ninja** CMake generator — UCRT64 has no `make`, so `-G "Unix Makefiles"`
    aborts with *"unable to find a build program"*,
  - **`-DNO_MARCH_NATIVE=ON`** — UxPlay defaults to `-march=native`, which tunes the
    binary to the build CPU and can `SIGILL` on a different/older clean machine,
  - a **full `bin/` DLL gather** (plus `json-glib`) instead of a per‑binary `ldd`,
    since dlopen'd plugins pull in DLLs a single `ldd uxplay.exe` never sees — and a
    **prune of the Vulkan** plugin (see above).
- **`rustc -V` prints the rustup manager blurb.** The `~/.cargo/bin` shims intercept
  the version flag, so scripts that parse `rustc -vV` get nothing. Put the **real
  toolchain** first on PATH:
  `export PATH="$HOME/.rustup/toolchains/stable-x86_64-pc-windows-msvc/bin:$PATH"`.

---

## macOS

### 🛠 Setup / building the bundle

- **UxPlay isn't on Homebrew** (it was removed from core), so `build_macos` clones
  **FDH2/UxPlay** and builds it from source. Install the deps once:

  ```bash
  brew install cmake pkg-config openssl@3 libplist dylibbundler \
    gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad
  bash desktop/scripts/build-uxplay-gstreamer.sh macos
  ```

- The bundler uses **`dylibbundler`** to rewrite install names so the gathered
  dylibs resolve by leaf name via `DYLD_LIBRARY_PATH` at runtime — that's what makes
  the bundle relocatable to a clean Mac.

### 🔴 The iPhone doesn't see the receiver

macOS speaks **Bonjour** natively, so discovery is usually solid — but the basics
still apply:

- **Same Wi‑Fi / subnet** as the phone (the shared rule above).
- **Firewall:** *System Settings → Network → Firewall* → allow incoming connections
  for the app (or `uxplay`). If "Block all incoming" is on, AirPlay can't be found.
- **AWDL / Wi‑Fi:** AirPlay leans on Apple's AWDL link. Keep Wi‑Fi **on** (even if the
  Mac is on Ethernet) and avoid VPNs that capture multicast.

### 🔴 The receiver starts but no video / "failed to load plugin"

- Confirm GStreamer can see the H.264 decoder: `gst-inspect-1.0 vtdec` (VideoToolbox)
  or `avdec_h264`. If a bundled run can't load a plugin, rebuild the tools so the
  dylib gather + `dylibbundler` pass runs cleanly.
- **Hardened runtime + entitlements:** the bundled GStreamer is loaded via `DYLD_*`
  env vars, which the hardened runtime blocks unless the app is signed with the
  **`com.apple.security.cs.allow-dyld-environment-variables`** entitlement. A signed
  release already carries it; an ad‑hoc local build may need it added.

---

## When all else fails

- **Prove the pipeline independently** of the phone. The MJPEG path is plain
  GStreamer — feed it a test source and read it back:

  ```bash
  # serve a test MJPEG stream exactly like the app does
  gst-launch-1.0 videotestsrc is-live=true ! videoconvert ! jpegenc quality=72 \
    ! multipartmux boundary=uxpframe ! tcpserversink host=127.0.0.1 port=8099 sync=false
  ```

  Connecting to that port should yield `--uxpframe` boundaries and JPEG frames
  (`FF D8 … FF D9`). If that works, your GStreamer is fine and the problem is
  discovery/network, not decoding.
- Still stuck on discovery? It's nearly always **mDNS reachability** — same subnet,
  firewall, router multicast, or (on Windows) a stray virtual adapter.

The mirror is for *seeing* the device, not driving it. Capture frames with **📸** to
drop straight into your store‑listing screenshots — capture from a real iPhone, no
OS screenshot or cable required.
