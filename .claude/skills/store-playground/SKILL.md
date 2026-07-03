---
name: store-playground
description: Set up and run the App Preview Playground on localhost, then load real listing text + screenshots from BOTH stores (App Store Connect + Google Play) via the Sync API. Use when the user wants to clone/run https://github.com/fighttechvn/app_marketing, start the local playground page (/playground/), pull store metadata and screenshots, or troubleshoot Sync / API keys / port 8092.
---

# Store Playground — setup, run, load from both stores

The **App Preview** repo (`fighttechvn/app_marketing`) is a local site that
assembles/previews an **App Store** + **Google Play** listing before shipping.
This skill drives an AI agent to: (1) get it running on localhost, and
(2) pull real **text + screenshots** from both stores into the tool.

Repo: **https://github.com/fighttechvn/app_marketing**

## Mental model — how "load from 2 stores" works

- `run.sh` → `python3 serve.py` serves everything on ONE origin (default port **8092**):
  `/` landing · `/playground/` the tool · `/docs/` · `/api/*` backend.
- The **Sync** button (or `GET /api/sync`) calls `server/stores.py::sync()`, which:
  - `fetch_appstore()` — App Store Connect API → iPhone/iPad screenshots + text
    (name, subtitle, keywords, promotional text, what's-new) per locale.
  - `fetch_play()` — Google Play API → phone screenshots + text (title, short/full
    description) per locale.
  - Writes **text** into `listing-current.json` and downloads **screenshots** into
    the Current gallery (`assets/current/` — `iphone-*.png`, `ipad-*.png`, `phone-*.png`).
  - This is the **Current** variant ("live on store"). The **New** variant lives in
    `listing.json` + `assets/new/`.
- Server binds **127.0.0.1 only** because `/api/*` exposes store credentials.

The static preview, New/Current toggle, **Try template**, and **Review Diff** need
**no credentials**. Only **Sync** and **Test keys** need real API keys.

## Step 1 — get the repo & run it (no creds needed to boot)

```bash
# if not already cloned:
git clone https://github.com/fighttechvn/app_marketing.git
cd app_marketing

./run.sh            # copies .env.example→.env if missing, builds docs once, serves on :8092
# ./run.sh --build  # force-rebuild the docs
```

Then open **http://localhost:8092/playground/**. At this point the tool works with
bundled dummy data — `Try template` fills the New variant so you can verify the UI.

Prereqs: **python3** (runtime). Node is only needed to build `/docs/` (optional —
Sync/Playground don't need it; a docs build failure just 404s `/docs/`).

If port 8092 is busy, `run.sh` kills the existing listener; or set `PORT=xxxx ./run.sh`.

## Step 2 — add store credentials (required ONLY for Sync / Test)

Edit `.env` (gitignored). Fill the store block — see `.env.example` and
`docs/src/content/docs/guides/api-keys.md`. Credentials may be a **path** or an
embedded **base64 single-line** (`*_B64`, preferred, self-contained):

```bash
# App Store Connect
ASC_KEY_ID="..."
ASC_ISSUER_ID="..."
BUNDLE_ID="com.example.app"
ASC_KEY_P8="./AuthKey_XXXXXXXXXX.p8"     # …or ASC_KEY_P8_B64="<base64 of the .p8>"

# Google Play
PLAYSTORE_PACKAGE_NAME="com.example.app"
PLAYSTORE_SERVICE_ACCOUNT_JSON="./sa.json"   # …or PLAYSTORE_SERVICE_ACCOUNT_JSON_B64="<base64>"
```

You can also paste them in the tool's **Import** (Export ▸ Env tab emits the `*_B64` form).
Restart `run.sh` after editing `.env` (it loads `.env` at startup).

## Step 3 — verify keys, then load from both stores

**Verify first** (doesn't save anything):

```bash
# The Import/Test flow POSTs the env to /api/test; from the UI use "Test keys".
curl -s http://localhost:8092/api/env | head       # what the server currently sees
```

**Load (Sync) — pulls text + screenshots from BOTH stores:**

- UI: click **⟳ Sync** in the Playground → fills the **Current** variant.
- Or headless:

```bash
curl -s http://localhost:8092/api/sync | python3 -m json.tool
# → {"ok":true,"appstore":{"iphone":N,"ipad":N},"googleplay":{"phone":N},
#    "locales":[...],"versionName":"..."}
```

After Sync:
- **Text** → `listing-current.json` (per-locale App Store + Google Play fields).
- **Screenshots** → `assets/current/iphone-*.png`, `ipad-*.png`, `phone-*.png`.
- In the tool, toggle **Current** to view live-store data; **Review Diff** vs New.

## Alternative — generate NEW screenshots with an agent (no store pull)

To create fresh store-spec screenshots (every required size, alpha stripped) for the
**New** variant instead of pulling Current from the store, follow
`docs/src/content/docs/guides/screenshot-prompts.md` (capture from simulator/emulator
→ resize → drop into `assets/new/`). Required sizes: iPhone 6.9" 1320×2868,
iPad 13" 2064×2752, Android phone 1344×2688, icon 1024²/512² **no alpha**.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `/api/sync` 500 `missing ASC_KEY_ID` etc. | Credential block in `.env` incomplete → fill Step 2, restart `run.sh`. |
| Sync 401/403 from a store | Key lacks access / wrong `BUNDLE_ID` / `PLAYSTORE_PACKAGE_NAME`. Run **Test keys** to isolate which store. |
| `/docs/` 404 | Astro build failed/skipped — harmless for Sync/Playground. `./run.sh --build` to rebuild, needs `npm`. |
| Port busy | `run.sh` kills the old listener; or `PORT=8093 ./run.sh`. |
| No screenshots after Sync | The store has none for that locale, or the app/version has no uploaded media yet. |
| Can't reach from another machine | By design — binds 127.0.0.1 only (creds). Use SSH tunnel if you must. |

See `AGENT_PROMPT.md` in this skill folder for a copy-paste prompt that hands the
whole flow to an AI agent.
