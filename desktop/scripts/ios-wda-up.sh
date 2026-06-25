#!/usr/bin/env bash
#
# ios-wda-up.sh — one command to get WebDriverAgent live for the iPhone tab.
#
#   ./ios-wda-up.sh [UDID]
#
# Automates the whole go-ios sequence: install (if missing) → iOS 17+ USB tunnel
# (asks for your password ONCE — required, only root can open the interface) →
# runwda → wait until WDA answers. Then open the 🍎 iPhone tab and press ⟳.
set -euo pipefail

UDID="${1:-}"
[ -n "$UDID" ] || UDID="$(idevice_id -l 2>/dev/null | head -1)"
[ -n "$UDID" ] || { echo "✗ no iPhone detected — plug in & trust the device"; exit 1; }
echo "→ device: $UDID"

# 1) go-ios (the `ios` CLI)
if ! command -v ios >/dev/null 2>&1; then
  echo "→ installing go-ios (npm i -g go-ios)…"
  npm install -g go-ios
fi

# 2) iOS 17+ RemoteXPC tunnel — needs root; skip if one is already running.
if [ "$(ios tunnel ls 2>/dev/null)" = "[]" ] || [ -z "$(ios tunnel ls 2>/dev/null)" ]; then
  echo "→ starting USB tunnel (sudo — enter your password; leave it running)…"
  sudo nohup ios tunnel start >/tmp/ios-tunnel.log 2>&1 &
  sleep 3
else
  echo "→ tunnel already running"
fi

# 3) WebDriverAgent runner
echo "→ launching WebDriverAgent…"
nohup ios runwda --udid="$UDID" >/tmp/ios-runwda.log 2>&1 &

# 4) wait until WDA answers on :8100 (forwarded with iproxy)
echo -n "→ waiting for WDA"
pkill -f "iproxy 8100:8100" 2>/dev/null || true
iproxy 8100:8100 -u "$UDID" >/dev/null 2>&1 &
IPROXY_PID=$!
for i in $(seq 1 40); do
  if curl -s --max-time 2 http://127.0.0.1:8100/status >/dev/null 2>&1; then
    kill "$IPROXY_PID" 2>/dev/null || true
    echo ""; echo "✓ WebDriverAgent is up — open the 🍎 iPhone tab and press ⟳"
    exit 0
  fi
  echo -n "."; sleep 1
done
kill "$IPROXY_PID" 2>/dev/null || true
echo ""; echo "⚠️  WDA didn't answer yet. Check /tmp/ios-runwda.log and /tmp/ios-tunnel.log, then retry."
exit 1
