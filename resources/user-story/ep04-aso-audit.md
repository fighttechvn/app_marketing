# EP04: Store SEO / ASO Audit User Stories

Feature: per-store, per-locale character-limit and completeness checks surfaced inline (the "ASO checks" panel + live counters).

## EP04.US001: Audit field lengths against store limits
As a developer, I want each metadata field checked against its store's character limit so that I never submit an over-length field.

Acceptance criteria:
- Toggling "ASO checks" shows a per-field audit for the active store and locale.
- App Store fields and limits: name 30, subtitle 30, keywords 100, promotionalText 170, description 4000, whatsNew 4000.
- Google Play fields and limits: title 30, shortDescription 80, fullDescription 4000, changelog 500.
- Each field shows a count badge: green within limit, red over limit.

## EP04.US002: See counts live while editing
As an editor, I want counters to update as I type so that I can trim copy in real time.

Acceptance criteria:
- Inline editing updates the ASO badges immediately (the ASO panel re-renders without a full page re-render).
- Bundle id (iOS) and package name (Android) are shown in code format for reference.

## EP04.US003: Catch empty required fields
As a publisher, I want empty required fields flagged so that I don't ship an incomplete listing.

Acceptance criteria:
- Empty fields are visibly distinguishable from filled ones.
- The audit is locale-aware: switching locale re-audits that locale's values.
