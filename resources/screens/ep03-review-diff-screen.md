# Review Diff (Current → New)

## Layout Mode: Tab-based modal

```
┌──────────────────────────────────────────────────────────────┐
│ Review changes — Current → New                          [✕]  │
├──────────────────────────────────────────────────────────────┤
│ [ Text & metadata ] [ Screenshots ]                          │
├──────────────────────────────────────────────────────────────┤
│  ── App ───────────────────────────────────────────────────  │
│  name            [CHG]  ~~Old name~~   →   New name           │
│  subtitle        [ADD]                 →   New subtitle       │
│  ── en-US ─────────────────────────────────────────────────  │
│  keywords        [CHG]  ~~old,kw~~     →   new,kw             │
│                                                              │
│  (Screenshots tab)                                           │
│  iPhone   Current 3 → New 4                                  │
│   #1 [▢ cur] → [▢ new] [CHG]   #4 [ — ] → [▢ new] [ADD]      │
├──────────────────────────────────────────────────────────────┤
│ 4 text field(s) · 2 screenshot change(s) · Current → New     │
│                                   [ Close ] [ Looks good ✓ ]  │
└──────────────────────────────────────────────────────────────┘
```

## Components
- Tab bar: Text & metadata | Screenshots.
- Text rows: field name + CHG/ADD/REM badge, old (red strikethrough) → new (green).
- Screenshot rows: per gallery, slot-aligned Current → New thumbnails with badges.
- Fullscreen lightbox: click a thumbnail to zoom (Esc / backdrop closes).
- Footer: change summary + Close / Looks good.

## States
- No Current synced: all New screenshots show ADD.
- Mixed: CHG / ADD / REM badges per row.

## Events
- TabSwitch → show text or screenshot pane.
- ThumbClick → open lightbox.
- Close / LooksGood → dismiss modal.

## SRS Export
- `resources/srs.sh` renders this document inside `Screens / UI Surfaces`.
