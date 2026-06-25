# First-Release Checklist

## Layout Mode: Full-screen modal (grouped)

```
┌──────────────────────────────────────────────────────────────┐
│ First-release checklist                  [Reset]        [✕]  │
│ ████████████████░░░░░░░░░░░░  62%                            │
│ Tags: [WEB UI]=console  [API]=scriptable  [DECLARATION]=true │
├──────────────────────────────────────────────────────────────┤
│ ▸ Accounts & signing                                        │
│   [x] Apple Developer Program active            [WEB UI]     │
│   [x] App Store Connect API key (.p8 path)      [API]        │
│   [ ] Google Play service account (Release Mgr) [API]        │
│ ▸ App records (one-time)                                     │
│   [x] ASC app record created                                │
│ ▸ Listing content                                           │
│   [ ] iOS screenshots 6.9"/6.7", iPad 12.9"     [WEB UI]     │
│   [x] Icon 1024/512 no alpha · feature 1024×500             │
│ ▸ Build · ▸ Version requirements · ▸ Submit                  │
│ ▸ Known first-submission rejections                         │
└──────────────────────────────────────────────────────────────┘
```

## Components
- Progress bar: live percent of checked items.
- Groups: Accounts & signing, App records, Listing content, Build, App Store version requirements, Submit, Known rejections.
- Item: checkbox + label + tag (WEB UI / API / DECLARATION).
- Reset: clears all + localStorage.

## States
- Restored: checkbox state from `store-release-checklist-v1`.
- In progress: percent < 100.
- Complete: percent = 100.

## Events
- ToggleItem → recompute percent → persist.
- Reset → clear all + storage.

## SRS Export
- `resources/srs.sh` renders this document inside `Screens / UI Surfaces`.
