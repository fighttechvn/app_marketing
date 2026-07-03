# Agent prompt — run the Playground & load both stores

Copy-paste one of these to an AI coding agent (Claude Code, etc.).

---

## Prompt A — full setup + run + load from both stores

```text
Repo: https://github.com/fighttechvn/app_marketing

Goal: get the App Preview Playground running on localhost and load real listing
TEXT + SCREENSHOTS from BOTH stores (App Store Connect + Google Play).

Do this:
1. Clone the repo (skip if already present) and cd into it.
2. Run `./run.sh`. It copies .env.example→.env if missing and serves everything on
   http://localhost:8092 (/, /playground/, /docs/, /api/*). python3 is the only
   runtime dependency. If port 8092 is busy it kills the old listener.
3. Confirm the tool is up: `curl -s http://localhost:8092/playground/ | head`.
4. Ask me for store credentials if not already in .env, then set in .env:
   - App Store Connect: ASC_KEY_ID, ASC_ISSUER_ID, BUNDLE_ID, and either
     ASC_KEY_P8 (path) or ASC_KEY_P8_B64 (base64 of the .p8, single line).
   - Google Play: PLAYSTORE_PACKAGE_NAME, and either
     PLAYSTORE_SERVICE_ACCOUNT_JSON (path) or ..._B64 (base64 of the JSON).
   Restart run.sh after editing .env.
5. Load from both stores: `curl -s http://localhost:8092/api/sync | python3 -m json.tool`.
   Expect {"ok":true,"appstore":{"iphone":N,"ipad":N},"googleplay":{"phone":N},...}.
6. Verify results: TEXT landed in listing-current.json (per-locale App Store +
   Google Play fields); SCREENSHOTS landed in assets/current/ (iphone-*.png,
   ipad-*.png, phone-*.png). Print the counts and the synced versionName.

Notes:
- The server binds 127.0.0.1 only (it exposes store creds under /api/*).
- If /api/sync 500s with "missing ASC_KEY_ID" etc., the .env credential block is
  incomplete. If it 401/403s, the key lacks access or BUNDLE_ID /
  PLAYSTORE_PACKAGE_NAME is wrong — use the "Test keys" flow to isolate the store.
- /docs/ needs an Astro (npm) build and is irrelevant to Sync; a 404 there is fine.
Report: the URL, the /api/sync JSON, and the resulting file/screenshot counts.
```

---

## Prompt B — no-credentials smoke test (UI only)

```text
Repo: https://github.com/fighttechvn/app_marketing

Clone (if needed), then `./run.sh`. Open http://localhost:8092/playground/ and use
"Try template" to load demo data into the New variant — verify the New/Current
toggle, Review Diff, and the screenshot lightbox all work with the bundled dummy
data. No API keys needed. Report anything that doesn't render.
```
