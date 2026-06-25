#!/usr/bin/env bash
#
# build-pages.sh — assemble the FULL static site for GitHub Pages into ./_site:
#   <base>/             → landing (home.html)
#   <base>/playground/  → the tool (static; Sync/Test/Try-template need the backend)
#   <base>/docs/        → Astro docs + blog
#
# PAGES_BASE defaults to /app_marketing (repo fighttechvn/app_marketing).
set -euo pipefail
cd "$(dirname "$0")/.."                       # → repo root
PAGES_BASE="${PAGES_BASE:-/app_marketing}"
OUT="_site"
echo "→ Pages base: $PAGES_BASE"
rm -rf "$OUT"; mkdir -p "$OUT/playground"

# 1) Docs → <base>/docs  (umbrella links resolve to <base>/…)
( cd docs && { [ -d node_modules ] || npm ci; }; \
  SITE_BASE="$PAGES_BASE/docs" UMBRELLA_BASE="$PAGES_BASE" npm run build )
cp -R docs/dist "$OUT/docs"

# 2) Playground (static tool) → <base>/playground
cp index.html listing.json listing-current.json listing-template.json "$OUT/playground/"
cp -R assets "$OUT/playground/assets"

# 3) Landing → <base>/  (+ marketing assets)
cp home.html "$OUT/index.html"
cp -R screenshots "$OUT/screenshots"

# 3b) SRS report → <base>/srs-index.html  (regenerate from resources/, fall back
#     to the committed copy if the renderer is unavailable).
if [ -f resources/srs.sh ]; then bash resources/srs.sh >/dev/null 2>&1 || true; fi
[ -f srs-index.html ] && cp srs-index.html "$OUT/srs-index.html"

# 4) Rewrite root-absolute links in the landing to the Pages base.
python3 - "$OUT/index.html" "$PAGES_BASE" <<'PY'
import sys
f, base = sys.argv[1], sys.argv[2]
s = open(f, encoding="utf-8").read()
for pat, rep in (
    ('"/playground/', f'"{base}/playground/'),
    ('="/docs',       f'="{base}/docs'),
    ('href="/"',      f'href="{base}/"'),
    ('"/screenshots/', f'"{base}/screenshots/'),
    ('"/srs-index.html', f'"{base}/srs-index.html'),
):
    s = s.replace(pat, rep)
open(f, "w", encoding="utf-8").write(s)
print("rewrote landing links →", base)
PY

touch "$OUT/.nojekyll"     # serve _astro/ (underscore) dirs
echo "✓ Pages site assembled → $OUT  (root=$PAGES_BASE)"
