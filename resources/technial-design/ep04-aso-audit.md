# EP04 Technical Design: Store SEO / ASO Audit

## Technologies
- Client-side audit in `index.html` driven by `DATA.limits` and the active locale.
- Inline count badges + a toggleable ASO panel; `updateAso()` re-renders only the audit.

## Screen Layout
- Source: `resources/screens/ep04-aso-audit-screen.md`

## Entry Points
- `index.html` — "ASO checks" toggle, per-field count badges, `updateAso()`.
- `DATA.limits.appstore` and `DATA.limits.googleplay` (also emitted by `server/stores.py` into `listing-current.json`).

## Flow
1. User toggles "ASO checks" (or edits a field).
2. For the active store + locale, read each field value length.
3. Compare against the field's limit; render a green (≤limit) or red (>limit) badge.
4. Empty required fields are flagged distinctly.
5. Switching locale or store re-audits.

## Flow Diagram
```mermaid
flowchart TD
  A[Toggle ASO / edit field] --> B[Resolve store + locale]
  B --> C[For each field: len(value)]
  C --> D{len <= limit?}
  D -->|Yes| E[Green badge]
  D -->|No| F[Red badge]
  C --> G{empty & required?}
  G -->|Yes| H[Flag empty]
  E --> I[Render ASO panel]
  F --> I
  H --> I
```

## Entities
| Entity | Purpose | Fields |
|---|---|---|
| LimitSet (appstore) | iOS limits | name 30, subtitle 30, keywords 100, promotionalText 170, description 4000, whatsNew 4000 |
| LimitSet (googleplay) | Android limits | title 30, shortDescription 80, fullDescription 4000, changelog 500 |
| AuditRow | One field check | `field`, `length`, `limit`, `status: ok|over|empty` |

## Tests
- Boundary cases at exactly the limit and limit+1.
- Live update on inline edit (badge flips color without full re-render).
- Locale-aware re-audit.

## Verification
```bash
# In the playground: toggle ASO checks, type past a limit, watch the badge turn red.
```
