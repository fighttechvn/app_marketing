# Device Mirror & Preview Panel

## Layout Mode: Right-side rail + slide-out panel

```
┌──────────────────────────────────────────────┬────┐
│  Preview panel (resizable, ≥320px)      [↗][✕]│ ▐  │
│ ┌──────────────────────────────────────────┐ │ 📱 │
│ │ Android ▾  [⟳][▶ Live][⚡ scrcpy]         │ │ 🍎 │
│ │ ┌──────────────────────────────────────┐ │ │    │
│ │ │                                      │ │ │ ✕  │
│ │ │      [ live device screen ]          │ │ │    │
│ │ │       tap ● swipe ╱                   │ │ └────┘
│ │ └──────────────────────────────────────┘ │ │
│ │ [▭ Recents][○ Home][◁ Back][🔉][🔊][⏻]   │ │
│ │ [ type text… ] [Send][⏎][⌫]              │ │
│ │ connected · 12.5 fps                      │ │
│ └──────────────────────────────────────────┘ │
│ Tabs also: 🍎 iPhone (WDA MJPEG) · Web · Media · Markdown │
└──────────────────────────────────────────────┴────┘
```

## Components
- Rail: 📱 Android · 🍎 iPhone · Web · Media · Markdown · ✕ close.
- Device selector + Refresh/Scan; Live toggle; scrcpy (Android) / Start WDA (iOS).
- Mirror area: screencap/MJPEG with tap ripple + swipe trail; FPS readout.
- Navigator buttons + text input.
- Media/Markdown tabs render local files via `/api/preview-file`.

## States
- Scanning: "scanning…" until devices resolve.
- Connected: model + fps / resolution shown.
- Tool missing: "adb missing" / "WDA not running" / setup helper.

## Events
- Refresh/Scan → list devices.
- Live → start screencap poll / MJPEG stream.
- TapMirror → POST input (tap/swipe) with feedback.
- NavButton / SendText → key/button/text event.

## SRS Export
- `resources/srs.sh` renders this document inside `Screens / UI Surfaces`.
