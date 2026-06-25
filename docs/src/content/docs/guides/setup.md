---
title: Setup — install and run App Preview
description: Step-by-step guide to install the prerequisites, run the store-preview site locally, and open the Playground, docs, and blog.
sidebar:
  order: 1
---

This guide walks you from a fresh clone to a running site — the **landing page**,
the interactive **Playground**, and these **docs** — all served on one origin by
`run.sh`.

## 1. Prerequisites

| Tool | Needed for | Notes |
| --- | --- | --- |
| **Python 3.9+** | the server (`serve.py`) + Sync/Test | standard library only to serve |
| `pip` packages | Sync + Test keys | `pip install pyjwt cryptography google-api-python-client google-auth google-auth-httplib2` |
| **Node 18+** | building these docs | only at build time, not to run the Playground |

The static preview, New/Current toggle, **Try template**, and **Review Diff** work
with **no credentials and no Python packages** — you only need the `pip` packages
for the live **Sync** and **Test keys** features.

## 2. Run the whole site

From the project folder:

```sh
./run.sh            # builds the docs once, then serves everything
./run.sh --build    # force-rebuild the docs first
```

On start it prints every route and opens your browser:

```text
→ Site (landing):  http://localhost:8092/
→ Playground:      http://localhost:8092/playground/
→ Docs:            http://localhost:8092/docs/
→ Blog:            http://localhost:8092/docs/blog/
```

The server binds **127.0.0.1 only**, because `/api/*` exposes store credentials —
never serve it on the LAN.

:::note
Working on the docs alone? `cd docs && npm install && npm run dev` serves them at
the root, so this page is at **http://localhost:4321/guides/setup/**. In the full
site (`run.sh`) the same page lives under **/docs/** — e.g.
`http://localhost:8092/docs/guides/setup/`.
:::

## 3. First run

1. Open **http://localhost:8092/** → the landing page, with the live Playground embedded.
2. Click **Open Playground** (or go to `/playground/`).
3. **New** and **Current** both start empty. Press **✨ Try template** to load the
   bundled demo into **New**, or drop in your own screenshots.

## 4. Add credentials (for Sync / Test)

To pull live data and verify keys you need App Store Connect + Google Play API
credentials in a `.env`:

1. Create the keys — see [Get your API keys](/guides/api-keys/) and
   [how to get each .env value](/guides/env-values/).
2. In the Playground, open **⤒ Import → Env**, paste your `.env`, and click
   **🔌 Test keys** — it verifies both stores without saving.
3. When both are ✓, **Save .env to local**, then press **⟳ Sync** to load your live
   listing into **Current**.

## 5. Next steps

- [Usage](/guides/usage/) — Try template, Sync, Review Diff, ASO checks, checklist.
- [The integrated site](/guides/the-site/) — how `/`, `/playground/`, `/docs/` fit together.
- [Generate store screenshots (agent prompts)](/guides/screenshot-prompts/).
- [Build a macOS desktop app](/guides/desktop-app/).
- [Requirements spec (SRS)](https://fighttechvn.github.io/app_marketing/srs-index.html) — the full product spec with **Docs / Flow / Board** views.

## Troubleshooting

- **Page won't load over `file://`** — browsers block `fetch()` there; always serve
  over http (`./run.sh` or `python3 serve.py`).
- **`/guides/setup/` 404 on port 8092** — in the full site the docs live under
  `/docs/`, so use `http://localhost:8092/docs/guides/setup/`.
- **App Store 401 on Test keys** — the `ASC_KEY_ID` / `ASC_ISSUER_ID` / `.p8` don't
  match a valid key (placeholder or truncated base64). See
  [env values](/guides/env-values/#verify-before-relying-on-them).
- **Sync says credentials missing** — you haven't **Saved** the `.env` yet, or it
  lacks the App Store / Play keys.
