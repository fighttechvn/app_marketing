"""Android device mirror + remote control via adb (+ scrcpy for a native window).

Localhost-only server, so shelling out to adb/scrcpy is acceptable (no LAN
exposure). Gesture coordinates are device PIXELS — the frontend maps clicks via
the screenshot's natural size.
"""
import os, shutil, subprocess
from .util import find_bin, have

ADB = find_bin("adb", "ADB_BIN")
SCRCPY = find_bin("scrcpy", "SCRCPY_BIN")

# The `emulator` binary lives in <sdk>/emulator — NOT platform-tools, and NOT the
# legacy <sdk>/tools/emulator (a deprecated x86 stub that crashes on Apple
# Silicon). PATH often only has the legacy one, so resolve <sdk>/emulator/emulator
# explicitly, deriving the SDK root from $ANDROID_HOME or the located adb.
def _find_emulator():
    env = os.environ.get("EMULATOR_BIN")
    if env and os.path.exists(env):
        return env
    home = os.path.expanduser("~")
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT")]
    # adb is <sdk>/platform-tools/adb → SDK root is two levels up
    if "platform-tools" in (ADB or ""):
        roots.append(os.path.dirname(os.path.dirname(ADB)))
    roots += [os.path.join(home, "Library/Android/sdk"), os.path.join(home, "Android/Sdk")]
    for r in roots:
        if r:
            cand = os.path.join(r, "emulator", "emulator")
            if os.path.exists(cand):
                return cand
    return shutil.which("emulator") or "emulator"

EMULATOR = _find_emulator()

_SCRCPY_PROCS = {}  # serial -> Popen (native high-FPS windows we launched)
_AVD_PROCS = {}     # avd name -> Popen (emulators we booted)

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


# ---- Android emulator (AVD) management -------------------------------------
# A booted emulator shows up in `adb devices` as emulator-NNNN and is then
# driven by the exact same mirror/control code as a physical phone. These two
# helpers only handle listing the available AVDs and booting one.

def _running_avds():
    """Names of AVDs that are currently booted (matched via `adb emu avd name`)."""
    names = set()
    if not have(ADB):
        return names
    out, _, rc = _adb(["devices"], timeout=10)
    if rc != 0:
        return names
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("emulator-") and parts[1] == "device":
            o, _, r = _adb(["emu", "avd", "name"], serial=parts[0], timeout=6)
            nm = o.splitlines()[0].strip() if (r == 0 and o.strip()) else ""
            if nm:
                names.add(nm)
    return names


def emu_avds():
    """List installed Android Virtual Devices + which are already booted."""
    if not have(EMULATOR):
        return {"ok": False, "avds": [],
                "error": "emulator not found (install via Android Studio, or set EMULATOR_BIN)"}
    try:
        out, err, rc = run_emulator(["-list-avds"])
    except OSError as e:
        return {"ok": False, "avds": [], "error": "emulator not runnable (%s): %s" % (EMULATOR, e)}
    if rc != 0:
        return {"ok": False, "avds": [], "error": err.strip() or "emulator -list-avds failed"}
    running = _running_avds()
    avds = [{"name": n.strip(), "running": n.strip() in running}
            for n in out.splitlines() if n.strip() and not n.startswith("INFO")]
    return {"ok": True, "avds": avds, "emulator": EMULATOR}


def emu_launch(name):
    """Boot an AVD headfully; it then appears in adb devices for mirror/control."""
    if not have(EMULATOR):
        return {"ok": False, "error": "emulator binary not found"}
    if not name:
        return {"ok": False, "error": "no AVD name"}
    proc = _AVD_PROCS.get(name)
    if proc and proc.poll() is None:
        return {"ok": True, "already": True}
    _AVD_PROCS[name] = subprocess.Popen(
        [EMULATOR, "-avd", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"ok": True, "launched": True}


def run_emulator(args, timeout=15):
    """Run the emulator CLI (separate from _adb since it's a different binary)."""
    p = subprocess.run([EMULATOR] + list(args), capture_output=True, timeout=timeout)
    return p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), p.returncode
