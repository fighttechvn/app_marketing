---
title: API endpoints
description: The serve.py backend endpoints (also rendered interactively via Scalar).
sidebar:
  order: 2
---

`serve.py` adds these JSON endpoints to the static page. They are **localhost
only**. For an interactive, try-it reference see the
[API reference (interactive)](/api/) page (rendered with Scalar from
[`openapi.yaml`](/openapi.yaml)).

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/sync` | Pull live App Store + Play listing → writes `listing-current.json` + `assets/current/` |
| `GET` | `/api/env` | Dump the Sync env vars (file creds emitted as base64) for the Export ▸ Env tab |
| `POST` | `/api/env` | Save a pasted `.env` to local (first-time only; `?force=1` to overwrite) |
| `POST` | `/api/test` | Verify the posted `.env` creds against both store APIs **without saving** |
| `POST` | `/api/apply-template` | Copy `assets/template/` → `assets/new/` and write `listing.json` (Try template) |

### Bodies

- `POST /api/env` and `POST /api/test` take the raw `.env` text as the request body
  (`Content-Type: text/plain`).
- `POST /api/apply-template` takes no body.

### Example

```sh
# verify keys without saving
curl -s -X POST --data-binary @.env http://127.0.0.1:8092/api/test | jq
# => { "ok": true,
#      "appstore":   { "ok": true, "detail": "OK — GoBrain (vn.fighttech.go2048)" },
#      "googleplay": { "ok": true, "detail": "OK — edit access to vn.fighttech.go2048 (SA ...)" } }
```
