---
title: The integrated site
description: One local site — landing, Playground, and docs — served by run.sh.
sidebar:
  order: 4
---

`run.sh` serves everything as **one site** via the `serve.py` umbrella, so the
landing page, the interactive tool, and these docs live under a single origin.

## Routes

| Route | What | Served from |
| --- | --- | --- |
| `/` | Landing page (product intro) | `home.html` |
| `/playground/` | The store-preview tool (Sync, Diff, Test, Try template) | `index.html` + `assets/`, `listing*.json` |
| `/docs/` | These docs + blog (built Astro/Starlight) | `docs/dist/` |
| `/docs/blog/` | Blog | `docs/dist/blog/` |
| `/docs/api/` | Interactive API reference (Scalar) | `docs/dist/api/` |
| `/api/*` | Backend endpoints used by the Playground | `serve.py` |

## Run it

```sh
./run.sh            # builds docs if needed, then serves the whole site
./run.sh --build    # force-rebuild the docs first
```

On start it prints every root link. The server binds **127.0.0.1 only** because
`/api/*` exposes store credentials.

## How routing works

`serve.py` overrides `translate_path`:

- `/` → `home.html` (falls back to the tool if there's no landing page)
- `/docs/…` → `docs/dist/…` (only if the docs have been built)
- `/playground/…` → the tool directory (relative `assets/`, `listing.json` resolve here)
- anything else → the tool directory

Each mount is guarded by existence, so a tool-only deployment (no `home.html`,
no `docs/dist`) still serves the Playground at `/`.

## Deploying

`.github/workflows/deploy.yml` runs `scripts/build-pages.sh` to assemble the **full
static site** (landing + Playground + docs) into `_site/` and publishes it to
**https://fighttechvn.github.io/app_marketing/** — `/` landing, `/playground/` the
static tool, `/docs/` these docs.

```sh
PAGES_BASE=/app_marketing bash scripts/build-pages.sh   # build _site/ locally
```

The Playground's backend (Sync / Test / Apply) needs `serve.py`, so those are inert
on Pages — for the fully interactive tool, **self-host** via `run.sh` or the
[desktop app](/guides/desktop-app/).
