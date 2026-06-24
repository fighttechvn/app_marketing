#!/usr/bin/env bash
#
# run.sh — serve the integrated site (landing + Playground + docs) on one origin.
#
#   ./run.sh            serve everything (builds docs once if dist/ is missing)
#   ./run.sh --build    force-rebuild the docs first
#   ./run.sh --gen      regenerate listing.json from .env + APP_DIST first (real data)
#
# Routes: /  (landing) · /playground/ (tool) · /docs/ (docs+blog) · /api/* (backend)
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { cp .env.example .env; echo "→ created .env from .env.example"; }
set -a; . ./.env; set +a
PORT="${PORT:-8092}"

case "${1:-}" in
  --gen)   python3 gen-listing.py || echo "⚠️  gen-listing.py failed — serving bundled listing.json" ;;
  --build) BUILD_DOCS=1 ;;
esac

# Build the docs (Astro/Starlight) so /docs/ is available. Built once unless --build.
if [ -d docs ]; then
  if [ "${BUILD_DOCS:-0}" = "1" ] || [ ! -d docs/dist ]; then
    echo "→ building docs (Astro)…"
    ( cd docs && [ -d node_modules ] || npm install --no-audit --no-fund; npm run build ) \
      || echo "⚠️  docs build failed — /docs/ will 404 until fixed"
  fi
fi

if lsof -ti "tcp:$PORT" >/dev/null 2>&1; then
  echo "→ port $PORT busy; stopping existing listener"
  lsof -ti "tcp:$PORT" | xargs kill 2>/dev/null || true; sleep 1
fi

BASE="http://localhost:$PORT"
cat <<EOF

  GoBrain · Store Preview — integrated site
  ─────────────────────────────────────────
  → Site (landing):  $BASE/
  → Playground:      $BASE/playground/
  → Docs:            $BASE/docs/
  → Blog:            $BASE/docs/blog/
  → API reference:   $BASE/docs/api/
  → Backend API:     $BASE/api/sync  ·  /api/env  ·  /api/test  ·  /api/apply-template
  (Ctrl+C to stop)

EOF

[ "${OPEN_BROWSER:-true}" = "true" ] && (sleep 1; open "$BASE/" 2>/dev/null || true) &

export PORT
exec python3 serve.py
