#!/usr/bin/env bash
#
# Populate src-tauri/tools/ with a RELOCATABLE UxPlay + GStreamer so the desktop
# app can mirror an iPhone over AirPlay with no system install (server/airplay.py
# runs tools/uxplay and points GStreamer at tools/gstreamer — see _spawn_env()).
#
#   tools/
#     uxplay(.exe)
#     gstreamer/
#       bin/                 # (Windows) GStreamer + dependency DLLs
#       lib/                 # shared libs (gathered, leaf-name resolvable)
#         gstreamer-1.0/     # plugins (.so/.dll), dlopen'd at runtime
#
# Run BEFORE `tauri build` (build.sh does this on macOS; CI does it for Windows).
# Idempotent-ish: it wipes tools/ (except README) and repopulates.
#
# ─────────────────────────────────────────────────────────────────────────────
# NOTE: native bundling is inherently platform-specific and must be validated on
# the actual build runners (it can't be exercised cross-platform). The macOS path
# leans on `dylibbundler` to rewrite install names; the Windows path resolves DLLs
# with `ldd` inside MSYS2/ucrt64. If a plugin fails to load on a clean machine,
# the usual cause is a missing transitive dep — widen the gather step below.
# When tools/ is left empty the app falls back to a system UxPlay/GStreamer, so a
# skipped/failed run never breaks the rest of the build.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."                      # → desktop/
DESKTOP="$(pwd)"
TOOLS="$DESKTOP/src-tauri/tools"
GST="$TOOLS/gstreamer"

# Plugins UxPlay actually needs: h264 decode + raw video/audio conversion + the
# native video/audio sinks. Keeping the set tight holds the bundle size down.
GST_PLUGIN_PKGS_MAC=(gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad libplist)

reset_tools() {
  mkdir -p "$TOOLS"
  find "$TOOLS" -mindepth 1 ! -name README.md -delete 2>/dev/null || true
  mkdir -p "$GST/lib/gstreamer-1.0" "$GST/bin"
}

# ── macOS: Homebrew deps + build UxPlay from source + dylibbundler ─────────────
# NOTE: UxPlay is NOT in Homebrew (removed from core) — `brew install uxplay` 404s.
# We build it from source (FDH2/UxPlay) unless UXPLAY_EXE points at a prebuilt one.
build_macos() {
  command -v brew >/dev/null || { echo "✗ Homebrew required on macOS"; exit 1; }
  echo "→ installing build deps + GStreamer via brew (idempotent)"
  for p in cmake pkg-config openssl@3 libplist dylibbundler "${GST_PLUGIN_PKGS_MAC[@]}"; do
    brew list "$p" >/dev/null 2>&1 || brew install "$p"
  done

  local UX="${UXPLAY_EXE:-}"
  if [ -z "$UX" ]; then
    echo "→ building UxPlay from source (FDH2/UxPlay)"
    local SRC="$DESKTOP/.uxplay-src"
    rm -rf "$SRC"; git clone --depth 1 https://github.com/FDH2/UxPlay "$SRC"
    ( cd "$SRC" && cmake . && make -j"$(sysctl -n hw.ncpu 2>/dev/null || echo 4)" )
    UX="$SRC/uxplay"
  fi
  [ -f "$UX" ] || { echo "✗ uxplay not built/found ($UX)"; exit 1; }
  cp "$UX" "$TOOLS/uxplay"; chmod +x "$TOOLS/uxplay"

  local GST_PREFIX; GST_PREFIX="$(brew --prefix gstreamer)"
  echo "→ copying GStreamer plugins from $GST_PREFIX/lib/gstreamer-1.0"
  cp -RL "$GST_PREFIX"/lib/gstreamer-1.0/*.dylib "$GST/lib/gstreamer-1.0/" 2>/dev/null || true
  # gst-plugins-{base,good,bad} install their plugins under their own kegs too.
  for p in "${GST_PLUGIN_PKGS_MAC[@]}"; do
    local pp; pp="$(brew --prefix "$p" 2>/dev/null || true)"
    [ -n "$pp" ] && cp -RL "$pp"/lib/gstreamer-1.0/*.dylib "$GST/lib/gstreamer-1.0/" 2>/dev/null || true
  done

  echo "→ gathering + rewriting dylib deps (dylibbundler) — uxplay + every plugin"
  # -of overwrite, -b no .app assumptions, -d dest, -p loader path; one -x per binary
  # whose deps we collect. dyld finds the gathered libs by leaf name via
  # DYLD_LIBRARY_PATH (set at runtime), so plugins resolve even off the build box.
  local XARGS=(-x "$TOOLS/uxplay")
  while IFS= read -r so; do XARGS+=(-x "$so"); done < <(find "$GST/lib/gstreamer-1.0" -name '*.dylib')
  dylibbundler -of -b -d "$GST/lib" -p '@loader_path' "${XARGS[@]}" || {
    echo "⚠️  dylibbundler reported issues — verify plugin loading on a clean Mac"; }
  rmdir "$GST/bin" 2>/dev/null || true       # macOS uses lib/, not bin/
  echo "✓ macOS tools bundled → $TOOLS"
}

# ── Windows: MSYS2 / ucrt64 ───────────────────────────────────────────────────
# Must run inside an MSYS2 ucrt64 shell (CI sets this up). UxPlay isn't in pacman,
# so we build it from source unless UXPLAY_EXE points at a prebuilt uxplay.exe.
build_windows() {
  local PREFIX="${MINGW_PREFIX:-/ucrt64}"
  echo "→ installing GStreamer + deps via pacman"
  pacman -S --needed --noconfirm \
    "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}-gstreamer" \
    "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}-gst-plugins-base" \
    "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}-gst-plugins-good" \
    "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}-gst-plugins-bad" \
    "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}-gst-libav" \
    "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}-json-glib" \
    "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}-libplist" || true
  # json-glib: several gst-plugins-bad plugins (e.g. codec2json) link it; without it
  # they fail to load with "specified module could not be found".
  # gst-libav supplies avdec_h264 — a pure-software H.264 decoder. gst-plugins-bad
  # also ships hardware decoders (d3d11h264dec/openh264dec), but bundling the
  # software fallback keeps the mirror decoding on a clean box whose GPU/driver
  # stack may not expose a DXVA H.264 decoder.

  local UX="${UXPLAY_EXE:-}"
  if [ -z "$UX" ]; then
    echo "→ building UxPlay from source (FDH2/UxPlay)"
    # Ninja (not "Unix Makefiles"): MSYS2/ucrt64 ships no `make`, so the Makefiles
    # generator can't find a build program and cmake aborts before compiler probing.
    pacman -S --needed --noconfirm "${MINGW_PACKAGE_PREFIX:-mingw-w64-ucrt-x86_64}"-{cmake,gcc,openssl,ninja} git || true
    local SRC="$DESKTOP/.uxplay-src"
    rm -rf "$SRC"; git clone --depth 1 https://github.com/FDH2/UxPlay "$SRC"
    # NO_MARCH_NATIVE: UxPlay defaults to -march=native, which tunes the binary to
    # the build box's CPU — a relocatable bundle must run on clean machines with a
    # different (older) CPU, where native-ISA instructions would SIGILL. Build for a
    # generic baseline instead.
    cmake -S "$SRC" -B "$SRC/build" -G Ninja -DNO_MARCH_NATIVE=ON
    cmake --build "$SRC/build"
    UX="$(find "$SRC/build" -name 'uxplay.exe' | head -1)"
  fi
  [ -n "$UX" ] && [ -f "$UX" ] || { echo "✗ uxplay.exe not found/built"; exit 1; }
  cp "$UX" "$TOOLS/uxplay.exe"

  echo "→ copying GStreamer plugins + DLLs"
  cp -R "$PREFIX"/lib/gstreamer-1.0 "$GST/lib/" 2>/dev/null || true
  # Ship the FULL $PREFIX/bin DLL set, not just uxplay.exe's direct `ldd` deps.
  # GStreamer plugins are dlopen'd at runtime and pull in transitive DLLs that an
  # ldd of uxplay.exe alone never sees, so a targeted gather misses them and the
  # plugin fails to load on a clean machine ("the specified module could not be
  # found"). Copying all of bin/ is the bulletproof "widen the gather": every
  # installed dependency is present. (Cost: a few dozen extra MB of DLLs.)
  cp -n "$PREFIX"/bin/*.dll "$GST/bin/" 2>/dev/null || true
  echo "✓ Windows tools bundled → $TOOLS ($(ls "$GST/bin"/*.dll 2>/dev/null | wc -l) DLLs)"
}

reset_tools
case "${1:-$(uname -s)}" in
  Darwin|darwin|macos) build_macos ;;
  *NT*|MINGW*|MSYS*|windows) build_windows ;;
  *) echo "✗ unsupported platform: ${1:-$(uname -s)} (macOS or Windows/MSYS2 only)"; exit 1 ;;
esac

du -sh "$TOOLS" 2>/dev/null || true
