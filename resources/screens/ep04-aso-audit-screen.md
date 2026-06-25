# Store SEO / ASO Audit Panel

## Layout Mode: Side panel (toggle)

```
┌───────────────────────────────────────────────┐
│ ASO checks · App Store · en-US           [✕]  │
├───────────────────────────────────────────────┤
│ name              "PulseFit: Habit Coach"  21/30 ✓│
│ subtitle          "Workouts, habits …"     28/30 ✓│
│ keywords          "fitness,workout,…"     104/100 ✗│
│ promotionalText   "Build daily habits…"    96/170 ✓│
│ description        …                      812/4000 ✓│
│ whatsNew           …                      140/4000 ✓│
│ Bundle ID         `com.demo.pulsefit`             │
├───────────────────────────────────────────────┤
│ (Google Play)                                  │
│ title             "PulseFit: Habit Coach"  21/30 ✓│
│ shortDescription  "Guided workouts…"       58/80 ✓│
│ fullDescription    …                      900/4000 ✓│
│ changelog          …                      120/500 ✓│
│ Package           `com.demo.pulsefit`             │
└───────────────────────────────────────────────┘
```

## Components
- Per-field row: label, value preview, count badge (used/limit).
- Green badge ≤ limit; red badge > limit; empty-required flag.
- Reference codes: bundle id (iOS) / package (Android).

## States
- Within limits: all green.
- Over limit: red badge on the offending field.
- Empty required: distinct flag.

## Events
- ToggleAso → show/hide panel.
- FieldEdit → `updateAso()` re-render badges live.
- LocaleSwitch / StoreSwitch → re-audit.

## SRS Export
- `resources/srs.sh` renders this document inside `Screens / UI Surfaces`.
