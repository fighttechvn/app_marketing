"""Android device mirror + remote control via adb (+ scrcpy for a native window).

Localhost-only server, so shelling out to adb/scrcpy is acceptable (no LAN
exposure). Gesture coordinates are device PIXELS — the frontend maps clicks via
the screenshot's natural size.
"""
import subprocess
from .util import find_bin, have

ADB = find_bin("adb", "ADB_BIN")
SCRCPY = find_bin("scrcpy", "SCRCPY_BIN")
_SCRCPY_PROCS = {}  # serial -> Popen (native high-FPS windows we launched)

# input keyname -> Android keycode (https://developer.android.com/reference/android/view/KeyEvent)
ADB_KEYS = {"back": 4, "home": 3, "recents": 187, "appswitch": 187, "power": 26,
            "volup": 24, "voldown": 25, "menu": 82, "enter": 66, "del": 67,
            "backspace": 67, "tab": 61, "search": 84, "play": 85, "wake": 224,
            "up": 19, "down": 20, "left": 21, "right": 22, "camera": 27, "notif": 83}


def _adb(args, serial=None, timeout=25, binary=False):
    """Run an adb command. Returns (stdout, stderr, rc); stdout is bytes when binary."""
    cmd = [ADB] + (["-s", serial] if serial else []) + list(args)
    p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
    return out, p.stderr.decode("utf-8", "replace"), p.returncode


def adb_devices():
    if not have(ADB):
        return {"ok": False, "error": "adb not found on PATH (set ADB_BIN)", "devices": []}
    out, err, rc = _adb(["devices", "-l"], timeout=15)
    devs = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        serial, state = parts[0], (parts[1] if len(parts) > 1 else "")
        model = next((t.split(":", 1)[1] for t in parts[2:] if t.startswith("model:")), "")
        devs.append({"serial": serial, "state": state, "model": model.replace("_", " "),
                     "scrcpy": serial in _SCRCPY_PROCS and _SCRCPY_PROCS[serial].poll() is None})
    return {"ok": True, "devices": devs, "adb": ADB, "scrcpy": have(SCRCPY)}


def adb_screen(serial=None):
    """Raw PNG of the current screen via `screencap -p` (binary stdout, no temp file)."""
    out, err, rc = _adb(["exec-out", "screencap", "-p"], serial=serial, timeout=20, binary=True)
    if rc != 0 or not out:
        raise RuntimeError(err.strip() or "screencap failed")
    return out


def adb_input(body):
    """Dispatch a remote-control gesture: tap / swipe / text / key / keyevent."""
    serial = body.get("serial") or None
    act = body.get("action")
    if act == "tap":
        _adb(["shell", "input", "tap", str(int(body["x"])), str(int(body["y"]))], serial=serial)
    elif act == "swipe":
        _adb(["shell", "input", "swipe", str(int(body["x1"])), str(int(body["y1"])),
              str(int(body["x2"])), str(int(body["y2"])), str(int(body.get("ms", 120)))], serial=serial)
    elif act == "text":
        # adb input text wants %s for spaces and no shell metacharacters
        t = str(body.get("text", "")).replace(" ", "%s")
        _adb(["shell", "input", "text", t], serial=serial)
    elif act == "key":
        code = ADB_KEYS.get(str(body.get("key", "")).lower())
        if code is None:
            return {"ok": False, "error": f"unknown key {body.get('key')}"}
        _adb(["shell", "input", "keyevent", str(code)], serial=serial)
    elif act == "keyevent":
        _adb(["shell", "input", "keyevent", str(int(body["code"]))], serial=serial)
    else:
        return {"ok": False, "error": f"unknown action {act}"}
    return {"ok": True}


def adb_scrcpy(serial=None):
    """Launch (or focus) a native scrcpy window — high-FPS mirror with full input."""
    if not have(SCRCPY):
        return {"ok": False, "error": "scrcpy not installed (brew install scrcpy)"}
    proc = _SCRCPY_PROCS.get(serial or "")
    if proc and proc.poll() is None:
        return {"ok": True, "already": True}
    cmd = [SCRCPY] + (["-s", serial] if serial else [])
    _SCRCPY_PROCS[serial or ""] = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    return {"ok": True, "launched": True}
