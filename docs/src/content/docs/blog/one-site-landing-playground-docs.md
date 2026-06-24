---
title: One site — landing, Playground, and docs
date: 2026-06-24
excerpt: We folded the marketing landing page, the interactive store-preview tool, and the docs into a single local site you start with one command.
tags: [tooling, docs]
---

The store-preview project used to be three separate things: a landing page, the
interactive tool, and the documentation. Now it's **one site**, served by a single
`serve.py` umbrella and started with `./run.sh`:

- **`/`** — the landing page introduces the product.
- **`/playground/`** — the interactive tool: Sync live data, Review Diff, Test keys, Try template.
- **`/docs/`** — these docs, plus the blog and the interactive API reference.

Everything shares one origin, so the Playground's `/api/*` calls just work, and
links between the marketing page and the docs are plain root-absolute paths.

Start it, and `run.sh` prints every route so you know exactly where to click:

```text
→ Site:        http://localhost:8092/
  Playground:  http://localhost:8092/playground/
  Docs:        http://localhost:8092/docs/
  Blog:        http://localhost:8092/docs/blog/
  API ref:     http://localhost:8092/docs/api/
```

See [The integrated site](/docs/guides/the-site/) for how the routing works and how
to deploy it.
