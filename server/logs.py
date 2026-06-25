"""Live log streaming from a device / emulator / simulator.

The source follows whatever target the panel selects:
  android → `adb logcat`        (real device AND emulator — same path)
  ios     → `idevicesyslog`     (real iPhone/iPad, libimobiledevice)
  sim     → `xcrun simctl spawn <udid> log stream`  (booted simulator)

`log_open()` returns the subprocess so the HTTP layer can relay its stdout to
the browser as a chunked text/plain stream; the HTTP layer terminates it when
the client disconnects (tab switch / panel close).
"""
import subprocess
from .util import find_bin, have
from . import android, ios

IDEVICESYSLOG = find_bin("idevicesyslog", "IDEVICESYSLOG_BIN")

# logcat priority letters, lowest→highest (used to build a `*:<L>` filter)
_ANDROID_LEVELS = {"V": "V", "D": "D", "I": "I", "W": "W", "E": "E"}


def log_cmd(kind, ident, level=None):
    """Build the streaming command for `kind` (android/ios/sim). Raises if the
    needed CLI is missing or the kind is unknown."""
    if kind == "android":
        if not have(android.ADB):
            raise RuntimeError("adb not found (set ADB_BIN)")
        cmd = [android.ADB] + (["-s", ident] if ident else []) + ["logcat", "-v", "time"]
        lv = _ANDROID_LEVELS.get(str(level or "").upper())
        if lv:
            cmd.append("*:" + lv)
        return cmd
    if kind == "sim":
        if not ios._have_xcrun():
            raise RuntimeError("xcrun/simctl not found — install Xcode")
        return [ios.XCRUN, "simctl", "spawn", ident or "booted", "log", "stream",
                "--style", "compact", "--color", "none"]
    if kind == "ios":
        if not have(IDEVICESYSLOG):
            raise RuntimeError("idevicesyslog not found (brew install libimobiledevice)")
        return [IDEVICESYSLOG] + (["-u", ident] if ident else [])
    raise RuntimeError("unknown log source: %s" % kind)


def log_open(kind, ident, level=None):
    """Spawn the log streamer; stdout is an unbuffered pipe of raw bytes."""
    cmd = log_cmd(kind, ident, level)
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)


def log_clear(kind, ident):
    """Clear the device log buffer — Android only (`adb logcat -c`)."""
    if kind == "android" and have(android.ADB):
        cmd = [android.ADB] + (["-s", ident] if ident else []) + ["logcat", "-c"]
        subprocess.run(cmd, capture_output=True, timeout=10)
        return {"ok": True}
    return {"ok": False, "error": "clear is only supported for Android (logcat)"}


def log_targets():
    """Everything we can stream from right now, for the panel's unified selector."""
    targets = []
    try:
        for x in android.adb_devices().get("devices", []):
            if x.get("state") == "device":
                targets.append({"kind": "android", "id": x["serial"],
                                "label": (x.get("model") or x["serial"]).strip() + " · Android"})
    except Exception:
        pass
    try:
        d = ios.ios_devices()
        for x in d.get("devices", []):
            targets.append({"kind": "ios", "id": x["udid"], "label": x["name"] + " · iOS"})
        for x in d.get("sims", []):
            if x.get("state") == "Booted":
                targets.append({"kind": "sim", "id": x["udid"], "label": x["name"] + " · Simulator"})
    except Exception:
        pass
    return {"ok": True, "targets": targets, "idevicesyslog": have(IDEVICESYSLOG)}
