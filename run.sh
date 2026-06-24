#!/usr/bin/env bash
#
# run.sh — serve the Store Listing Preview.
#
#   ./run.sh           serve the bundled data (listing.json + listing-current.json)
#   ./run.sh --gen     regenerate listing.json from .env + APP_DIST first (real data)
#
# Ships with dummy demo data, so `./run.sh` works out of the box. serve.py also
# exposes /api/sync (Sync button) when real store credentials are configured.
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { cp .env.example .env; echo "→ created .env from .env.example"; }
set -a; . ./.env; set +a
PORT="${PORT:-8092}"

if [ "${1:-}" = "--gen" ]; then
  python3 gen-listing.py || echo "⚠️  gen-listing.py failed — serving bundled listing.json"
fi

if lsof -ti "tcp:$PORT" >/dev/null 2>&1; then
  echo "→ port $PORT busy; stopping existing listener"
  lsof -ti "tcp:$PORT" | xargs kill 2>/dev/null || true; sleep 1
fi

URL="http://localhost:$PORT/"
echo "→ Store Preview: $URL   (Ctrl+C to stop)"
[ "${OPEN_BROWSER:-true}" = "true" ] && (sleep 1; open "$URL" 2>/dev/null || true) &

export PORT
exec python3 serve.py
