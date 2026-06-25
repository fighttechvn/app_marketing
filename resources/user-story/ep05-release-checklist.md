# EP05: First-Release Checklist User Stories

Feature: a full-screen, persisted checklist covering everything a first App Store + Google Play submission needs.

## EP05.US001: Work through a first-submission checklist
As a first-time publisher, I want a guided checklist so that I don't miss anything that would cause a rejection.

Acceptance criteria:
- "Release checklist" opens a full-screen modal grouped into sections: Accounts & signing, App records, Listing content, Build, App Store version requirements, Submit, and Known first-submission rejections.
- Each item is a checkbox with explanatory text.
- Items are tagged WEB UI (console-only), API (scriptable), or DECLARATION (must not be fabricated).

## EP05.US002: Track progress
As a user, I want to see how far along I am so that I know what's left.

Acceptance criteria:
- A progress bar shows percent complete and updates live as items are checked.
- Checkbox state persists in `localStorage` (`store-release-checklist-v1`).
- A Reset clears all items and the stored state.

## EP05.US003: Verify required assets and declarations
As a publisher, I want the checklist to enumerate concrete required assets so that I can confirm each one.

Acceptance criteria:
- Listing content section enumerates required screenshot sizes (iPhone 6.9"/6.7", iPad 12.9", Android phone), no-alpha icon rules, and per-locale metadata.
- App Store version section covers copyright, content rights, age rating, app privacy, pricing, and export compliance.
- Submit section covers iOS review submission state and Android production promotion.
