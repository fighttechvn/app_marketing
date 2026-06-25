# EP07: Device Mirror & Remote Control User Stories

Feature: a right-side preview panel that mirrors and remote-controls a real Android device (adb/scrcpy) or iPhone (WebDriverAgent), plus web/media/markdown preview tabs.

## EP07.US001: Mirror and control an Android device
As a developer, I want to see and drive a connected Android phone so that I can capture or QA screens without leaving the tool.

Acceptance criteria:
- The Android tab lists devices via `GET /api/adb/devices` (serial, state, model, scrcpy availability).
- "Live" polls `GET /api/adb/screen?serial=…` for a screencap stream with an FPS readout.
- Tapping/swiping the mirror sends `POST /api/adb/input` (tap/swipe/text/key) with on-image touch feedback.
- Navigator buttons (Recents/Home/Back/Vol/Power) and a text input send key/text events.
- "scrcpy" launches a native high-FPS window via `POST /api/adb/scrcpy`.

## EP07.US002: Mirror and control an iPhone
As a developer, I want to mirror a real iPhone so that I can preview live screens on iOS.

Acceptance criteria:
- The iPhone tab lists devices via `GET /api/wda/devices` and shows WDA status via `/api/wda/status`.
- "Start WDA" launches WebDriverAgent via `xcodebuild` (`POST /api/wda/launch`), auto-detecting signing team and project; a setup helper shows go-ios commands.
- "Live" streams MJPEG from `/api/wda/mjpeg?udid=…`, falling back to polling `/api/wda/screen`.
- Tap/swipe/text/buttons (Home, Vol, Lock) send `POST /api/wda/input` (logical points).
- A USB tunnel via `iproxy` forwards ports 8100/9100.

## EP07.US003: Preview web, media, and markdown
As a user, I want to open links, images, and docs in the side panel so that I can review supporting material in context.

Acceptance criteria:
- Clicking an in-page link opens it in the panel: media files → Media tab, `.md` → Markdown tab, else Web tab (iframe, `no-referrer`).
- Media tab renders image/video/audio from a file pick or `GET /api/preview-file?path=…`.
- Markdown tab renders `.md`/`.mdx` with a dependency-free converter.
- The panel is resizable (min 320px) and can pop out to a new tab.
