# EP01: Store Listing Preview User Stories

Feature: the interactive Playground (`index.html`) that renders a listing as it would appear on the App Store and Google Play, with editable metadata, screenshots, multi-locale, and a New vs Current variant model.

## EP01.US001: Preview a listing on both stores
As a developer, I want to see my listing rendered as a realistic App Store and Google Play mockup so that I know how it will look before I submit.

Acceptance criteria:
- A store toggle switches between **App Store** (iOS) and **Google Play** (Android) layouts.
- App Store view shows: app icon, name (≤30), subtitle (≤30), GET button, metadata row (rating/age/category/developer/language/version), iPhone + iPad screenshot galleries, promotional text, description, what's new, keyword chips.
- Google Play view shows: icon, title (≤30), developer, rating/downloads/age, Install button, phone + tablet screenshot sub-tabs, full description, what's new, app icon + feature graphic block, package id, short description.
- Empty/placeholder state renders without overflow when no listing is loaded.

## EP01.US002: Switch between New and Current variants
As a release manager, I want to flip between the **New** version I'm preparing and the **Current** version live on the store so that I always know which one I'm looking at.

Acceptance criteria:
- A variant toggle offers **New ⬆** and **Current**.
- **Current** is read-only; attempting drag-drop shows a "Current is locked" message.
- **New** is editable (text + screenshots).
- The active variant label is visible in the control bar.

## EP01.US003: Edit metadata and assets in place
As a developer, I want to edit text and swap screenshots directly on the preview so that I can iterate quickly.

Acceptance criteria:
- "Edit on page" enables `contenteditable` fields with dashed outlines; edits update the in-memory listing without losing caret position.
- Character counters turn red when a field exceeds its store limit (live).
- "Edit JSON" exposes the raw `listing.json` with Apply / Format / Download / Reset.
- Images can be added via "Load images…", drag-and-drop (whole page or per slot), or a directory pick; they auto-classify into iphone/ipad/phone/tablet/icon/feature-graphic by filename hint then aspect ratio.
- A toast confirms how many images landed in each gallery.

## EP01.US004: View the listing per locale
As a publisher with localized listings, I want to switch locale so that I can review each market's metadata and screenshots.

Acceptance criteria:
- Locale buttons are generated from the listing's `locales`.
- Switching locale updates all text, ASO counts, and (where present) screenshots live.
- The selected locale persists across reloads.

## EP01.US005: Use the tool in dark mode and multiple UI languages
As a user, I want a dark theme and a localized UI so that the tool fits my environment.

Acceptance criteria:
- Theme toggle (light/dark) persists to `localStorage`.
- Landing page UI is translatable to en, vi, ko, ar (RTL), ja.
- No flash of the wrong theme on load.
