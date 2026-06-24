# Store Preview — docs & blog (Astro Starlight)

Setup/usage docs, env-variable reference, an interactive API reference (Scalar),
and a blog for the store-listing preview tool.

## Develop

```sh
cd docs
npm install
npm run dev        # standalone docs at http://localhost:4321/docs
```

In the **integrated site** the docs are served at `/docs/` by `../run.sh`
(serve.py umbrella: `/` landing, `/Playground/` tool, `/docs/` these docs).
The base path comes from `SITE_BASE` (default `/docs`).

A **docs-only** static build is published to GitHub Pages at
**https://fighttechvn.github.io/app_marketing/** (built with `SITE_BASE=/app_marketing`).

## Build

```sh
npm run build      # static site → dist/
npm run preview
```

## Structure

| Path | What |
| --- | --- |
| `src/content/docs/guides/` | Setup, Usage |
| `src/content/docs/reference/` | Env variables, API endpoints |
| `src/content/docs/blog/` | Blog posts (starlight-blog) |
| `src/pages/api/index.astro` | Interactive API reference (Scalar from `public/openapi.yaml`) |
| `public/openapi.yaml` | OpenAPI 3.1 spec for the serve.py endpoints |

## Deploy to GitHub Pages (docs-only)

`.github/workflows/deploy.yml` (repo root) builds `docs/` with `SITE_BASE=/app_marketing`
via `withastro/action` on push to `main`, publishing to
**https://fighttechvn.github.io/app_marketing/**.

One-time: in the repo, **Settings → Pages → Build and deployment → Source = GitHub Actions**.

> The interactive **Playground** needs the Python backend (`serve.py`) for
> Sync/Test/Apply, so the full integrated site is best self-hosted via `run.sh`.
> GitHub Pages hosts the static docs only.
