# Store Listing Preview (Playground)

## Layout Mode: Split-panel (sticky control bar + store mockup)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Store Listing Preview · App Store + Google Play         [☾ theme] [lang]│
├────────────────────────────────────────────────────────────────────────┤
│ [App Store][Google Play]   [New ⬆][Current]   en-US│vi│ko│…             │
│ [📁 Open][✨ Try template][⟳ Sync][Review Diff]                          │
│ [ASO checks][Edit on page][Release checklist][Edit JSON][⤓ Export][⤒ Import][Load images…] │
│ ⤵ or drag images / a folder anywhere                                     │
├────────────────────────────────────────────────────────────────────────┤
│  APP STORE MODE                          │  GOOGLE PLAY MODE             │
│  ┌────────────────────────────────────┐  │  ┌─────────────────────────┐  │
│  │ [icon] App Name            [ GET ] │  │  │ Apps ▸                  │  │
│  │        Subtitle (≤30)         [↗] │  │  │ [icon] App Title (≤30)  │  │
│  │ Free · iPhone & iPad               │  │  │ Developer · ★ · 50K+    │  │
│  ├────────────────────────────────────┤  │  │ [ Install ]             │  │
│  │ ★★★★★ │ 4+ │ #1 │ Dev │ EN │ v1.4 │  │  ├─────────────────────────┤  │
│  ├────────────────────────────────────┤  │  │ [Phone (5)][Tablet (2)] │  │
│  │ iPhone  ▸ [▢ ▢ ▢ ▢] scroll ...    │  │  │ [▸ screenshots] ...     │  │
│  │ iPad    ▸ [▢ ▢ ▢] ...              │  │  │ About this app …        │  │
│  │ Promotional text (≤170)            │  │  │ What's new …            │  │
│  │ Description (≤4000) …              │  │  │ ┌ App icon ┐ ┌ Feature ┐ │  │
│  │ What's New (v1.4) …               │  │  │ │ Uploaded │ │ 1024×500 │ │  │
│  │ Keywords: [chip][chip][chip]       │  │  │ Package · short desc    │  │
│  └────────────────────────────────────┘  │  └─────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

## Components
- Store toggle: switches App Store ↔ Google Play layout.
- Variant toggle: New (editable) ↔ Current (read-only/locked).
- Locale buttons: generated from `DATA.locales`; switch all copy + screenshots.
- Action bar: Open folder, Try template, Sync, Review Diff, ASO checks, Edit on page, Release checklist, Edit JSON, Export, Import, Load images.
- Screenshot galleries: iphone/ipad (App Store), phone/tablet sub-tabs (Play).
- Graphics block (Play): app icon + feature graphic with status pills.

## States
- Initial: empty placeholder listing, no overflow.
- Loaded: `listing.json` rendered.
- Editing: dashed outlines on `contenteditable` fields; live counters.
- Current: locked; drag-drop shows "Current is locked".

## Events
- StoreToggle → re-render mockup.
- VariantToggle → swap New/Current; lock when Current.
- LocaleSelect → re-render copy/screenshots/ASO.
- EditOnPage → enable contenteditable.
- DropImages → classify by name → aspect ratio → assign gallery.

## SRS Export
- `resources/srs.sh` renders this document inside `Screens / UI Surfaces`.
