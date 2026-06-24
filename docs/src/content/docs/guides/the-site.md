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

The Playground needs the Python backend (`serve.py`) for Sync / Test / Apply, so
the full site is best **self-hosted** (run `serve.py` behind your own host).

For a static **docs-only** deploy to GitHub Pages, build with a matching base:

```sh
SITE_BASE=/app_marketing npm --prefix docs run build
# → https://fighttechvn.github.io/app_marketing/
```
