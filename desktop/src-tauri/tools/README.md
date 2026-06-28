# Bundled native tools — UxPlay + GStreamer (AirPlay iPhone-Mirror)

This directory is bundled into the app as a Tauri **resource** (`bundle.resources`
in `tauri.conf.json`). At runtime the Rust shell resolves `<resources>/tools` and
passes it to the Python sidecar as `--tools-dir`; `server/airplay.py` then runs the
bundled `uxplay` and points GStreamer at `tools/gstreamer` (see `_spawn_env()`).

It is populated by **`desktop/scripts/build-uxplay-gstreamer.sh`** during the build
(macOS via Homebrew + dylibbundler; Windows via MSYS2). It is intentionally NOT
committed (only this README is) — see `.gitignore`. When empty, the app falls back
to a system-installed UxPlay/GStreamer, so source runs and dev builds still work.

Expected layout after population:

```
tools/
  uxplay(.exe)
  gstreamer/
    bin/                 # (Windows) GStreamer + dependency DLLs
    lib/
      gstreamer-1.0/     # GStreamer plugins (.so / .dll) — dlopen'd at runtime
```
