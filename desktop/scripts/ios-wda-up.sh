#!/usr/bin/env bash
#
# ios-wda-up.sh — one command to get WebDriverAgent live for the iPhone tab.
#
#   ./ios-wda-up.sh [UDID]
#
# Launches WDA the reliable way: `xcodebuild test` on Appium's bundled
# WebDriverAgent project (works on iOS 18 where go-ios runwda can't, and needs
# NO sudo tunnel). Builds+signs+installs+runs the runner, then waits until WDA
# answers. Leave it running; open the 🍎 iPhone tab and it auto-connects.
#
# Signing: set WDA_TEAM_ID, or it auto-detects from the installed WDA app.
set -euo pipefail

UDID="${1:-}"
[ -n "$UDID" ] || UDID="$(idevice_id -l 2>/dev/null | head -1)"
[ -n "$UDID" ] || { echo "✗ no iPhone detected — plug in & trust the device"; exit 1; }
echo "→ device: $UDID"

WDA_PROJ="${WDA_PROJECT:-$(ls -d "$HOME"/.appium/node_modules/**/appium-webdriveragent/WebDriverAgent.xcodeproj 2>/dev/null | head -1 || true)}"
[ -n "$WDA_PROJ" ] || { echo "✗ WebDriverAgent.xcodeproj not found — run: appium driver install xcuitest"; exit 1; }
echo "→ WDA project: $WDA_PROJ"

# signing team — env override, else auto-detect from the installed WDA app
TEAM="${WDA_TEAM_ID:-}"
if [ -z "$TEAM" ] && command -v ios >/dev/null 2>&1; then
  TEAM="$(ios apps --udid="$UDID" 2>/dev/null | grep -oE '"application-identifier":"[A-Z0-9]+\.com\.facebook\.WebDriverAgentRunner' | grep -oE '[A-Z0-9]+\.com' | cut -d. -f1 | head -1 || true)"
fi
[ -n "$TEAM" ] && echo "→ signing team: $TEAM"

echo "→ launching WebDriverAgent via xcodebuild (first build ~1–3 min)…"
nohup xcodebuild -project "$WDA_PROJ" -scheme WebDriverAgentRunner \
  -destination "id=$UDID" -allowProvisioningUpdates CODE_SIGNING_ALLOWED=YES \
  ${TEAM:+DEVELOPMENT_TEAM=$TEAM} test > /tmp/wda-xcodebuild.log 2>&1 &

echo -n "→ waiting for WDA"
pkill -f "iproxy 8100:8100" 2>/dev/null || true
iproxy 8100:8100 -u "$UDID" >/dev/null 2>&1 &
IPROXY_PID=$!
for i in $(seq 1 90); do
  if curl -s --max-time 2 http://127.0.0.1:8100/status 2>/dev/null | grep -q '"ready":true'; then
    kill "$IPROXY_PID" 2>/dev/null || true
    echo ""; echo "✓ WebDriverAgent is up — open the 🍎 iPhone tab and press ⟳ (or it auto-connects)"
    exit 0
  fi
  echo -n "."; sleep 2
done
kill "$IPROXY_PID" 2>/dev/null || true
echo ""; echo "⚠️  WDA didn't answer. Check /tmp/wda-xcodebuild.log (signing?), or open the project in Xcode once."
exit 1
