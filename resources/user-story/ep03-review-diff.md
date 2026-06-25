# EP03: Review Diff User Stories

Feature: a side-by-side comparison of the **Current** (live) listing against the **New** (pending) listing, for text and screenshots.

## EP03.US001: Diff metadata field-by-field
As a release manager, I want a per-field text diff so that I can confirm exactly what is changing in this update.

Acceptance criteria:
- "Review Diff" opens a modal titled "Review changes — Current → New".
- The **Text & metadata** tab groups changes by section (App, then each locale).
- Each changed field shows the old value (red strikethrough) and new value (green) with a CHG / ADD / REM badge.
- Unchanged fields are not noise.

## EP03.US002: Diff screenshots slot-by-slot
As a designer, I want to compare screenshots per slot so that I can spot accidental swaps, additions, or removals.

Acceptance criteria:
- The **Screenshots** tab lists each gallery (iPhone, iPad, phone, tablet) with "Current N → New M".
- Each slot shows Current (left) and New (right) thumbnails with CHG / ADD / REM badges; missing slots show a "—" placeholder.
- Clicking a thumbnail opens a fullscreen lightbox (≤95vw × 90vh) captioned e.g. "New · #2 — iPhone"; Esc or backdrop closes it.

## EP03.US003: Summarize and dismiss
As a user, I want a summary and a clean exit so that I can close the review with confidence.

Acceptance criteria:
- The footer summarizes "X text field(s) · Y screenshot change(s) · Current → New".
- "Looks good ✓" and "Close" both dismiss the modal.
- If Current was never synced, the diff treats all New screenshots as additions (and says so implicitly via ADD badges).
