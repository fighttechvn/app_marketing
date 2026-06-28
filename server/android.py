"""Android device mirror + remote control via adb (+ scrcpy for a native window).

Localhost-only server, so shelling out to adb/scrcpy is acceptable (no LAN
exposure). Gesture coordinates are device PIXELS — the frontend maps clicks via
the screenshot's natural size.
"""
import os, re, time, shutil, secrets, subprocess
from .util import find_bin, have, exe_path, run
from . import config

ADB = find_bin("adb", "ADB_BIN")
SCRCPY = find_bin("scrcpy", "SCRCPY_BIN")

# Effective binaries: a user override in the Config / Paths dialog wins, else the
# PATH/SDK auto-detection above. Resolved per call so a config edit takes effect
# without restarting the server.
def adb_bin():      return config.get("adb") or ADB
def scrcpy_bin():   return config.get("scrcpy") or SCRCPY
def emulator_bin(): return config.get("emulator") or EMULATOR
def aapt_bin():     return config.get("aapt") or _find_aapt()


# aapt lives in <sdk>/build-tools/<ver>/aapt(.exe) — used to read an APK's package
# name + launchable activity so we can auto-open the app after installing it.
def _find_aapt():
    env = os.environ.get("AAPT_BIN")
    if env and exe_path(env):
        return exe_path(env)
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT")]
    if "platform-tools" in (ADB or ""):
        roots.append(os.path.dirname(os.path.dirname(ADB)))   # <sdk>/platform-tools/adb → <sdk>
    home = os.path.expanduser("~")
    roots += [os.path.join(home, "Library/Android/sdk"), os.path.join(home, "Android/Sdk")]
    for r in roots:
        bt = os.path.join(r, "build-tools") if r else ""
        if bt and os.path.isdir(bt):
            for ver in sorted(os.listdir(bt), reverse=True):     # newest build-tools first
                for tool in ("aapt2", "aapt"):
                    hit = exe_path(os.path.join(bt, ver, tool))
                    if hit:
                        return hit
    return shutil.which("aapt2") or shutil.which("aapt") or ""


def apk_package(path):
    """(package, launchable_activity) from `aapt dump badging` — ('', '') if unknown."""
    aapt = aapt_bin()
    if not have(aapt):
        return "", ""
    try:
        out, _, rc = run([aapt, "dump", "badging", path], timeout=30)
    except Exception:
        return "", ""
    pkg = re.search(r"package: name='([^']+)'", out or "")
    act = re.search(r"launchable-activity: name='([^']+)'", out or "")
    return (pkg.group(1) if pkg else ""), (act.group(1) if act else "")

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
            hit = exe_path(os.path.join(r, "emulator", "emulator"))   # <sdk>/emulator/emulator(.exe)
            if hit:
                return hit
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
    cmd = [adb_bin()] + (["-s", serial] if serial else []) + list(args)
    p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
    return out, p.stderr.decode("utf-8", "replace"), p.returncode


def adb_devices():
    if not have(adb_bin()):
        return {"ok": False, "error": "adb not found on PATH (set ADB_BIN or pin it in Config / Paths)", "devices": []}
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
    return {"ok": True, "devices": devs, "adb": adb_bin(), "scrcpy": have(scrcpy_bin())}


def adb_screen(serial=None):
    """Raw PNG of the current screen via `screencap -p` (binary stdout, no temp file)."""
    out, err, rc = _adb(["exec-out", "screencap", "-p"], serial=serial, timeout=20, binary=True)
    if rc != 0 or not out:
        raise RuntimeError(err.strip() or "screencap failed")
    return out


def adb_install(serial, path):
    """Install (or reinstall, keeping data) an APK onto the device — the target
    of dragging a build onto the Android frame. `path` is a local .apk/.apks the
    server can read (native drop gives a real path; browser upload writes a temp)."""
    if not have(adb_bin()):
        return {"ok": False, "error": "adb not found (set it in Config / Paths)"}
    if not path or not os.path.isfile(path):
        return {"ok": False, "error": "APK not found: %s" % path}
    args = ["install-multiple", "-r"] if path.lower().endswith(".apks") else ["install", "-r"]
    out, err, rc = _adb(args + [path], serial=serial, timeout=300)
    msg = (out or "") + (err or "")
    if rc != 0 or "Failure" in msg or "Error" in msg:
        return {"ok": False, "error": (msg.strip() or "install failed")[:300]}
    # Auto-open the freshly installed app (best-effort — needs aapt to read the
    # package + launchable activity; silently skipped if aapt isn't available).
    pkg, act = apk_package(path)
    launched = False
    if pkg:
        if act:
            _adb(["shell", "am", "start", "-n", "%s/%s" % (pkg, act)], serial=serial, timeout=20)
        else:
            _adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
                 serial=serial, timeout=20)
        launched = True
    return {"ok": True, "out": (out.strip() or "Success")[:200], "package": pkg, "launched": launched}


def adb_capture(serial, dest_dir):
    """Grab the current screen (screencap) and save a PNG into `dest_dir`.
    Returns the saved path so the UI can show a draggable thumbnail of it."""
    data = adb_screen(serial)
    os.makedirs(dest_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = "android-%s.png" % stamp
    path = os.path.join(dest_dir, name)
    n = 1
    while os.path.exists(path):              # avoid clobbering same-second captures
        name = "android-%s-%d.png" % (stamp, n); path = os.path.join(dest_dir, name); n += 1
    with open(path, "wb") as f:
        f.write(data)
    return {"ok": True, "path": path, "file": name}


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
    if not have(scrcpy_bin()):
        return {"ok": False, "error": "scrcpy not installed (brew install scrcpy)"}
    proc = _SCRCPY_PROCS.get(serial or "")
    if proc and proc.poll() is None:
        return {"ok": True, "already": True}
    cmd = [scrcpy_bin()] + (["-s", serial] if serial else [])
    _SCRCPY_PROCS[serial or ""] = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    return {"ok": True, "launched": True}


# ---- Wireless adb (mirror over Wi-Fi, no cable) ----------------------------
# Three ways in, all standard adb: (1) USB→Wi-Fi: flip a cabled device to TCP mode
# with `adb tcpip 5555`, read its IP, connect, unplug. (2) Direct `adb connect
# ip:5555` if Wi-Fi adb is already on. (3) `adb pair ip:port code` for Android 11+
# "Wireless debugging" first-time pairing, then connect. Once connected the Wi-Fi
# device is just another entry in `adb devices` — mirror/control code is unchanged.

def _device_ip(serial):
    """The device's Wi-Fi (wlan0) IPv4, for the USB→Wi-Fi auto-connect step."""
    out, _, _ = _adb(["shell", "ip", "-f", "inet", "addr", "show", "wlan0"], serial=serial, timeout=8)
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out or "")
    if m:
        return m.group(1)
    out, _, _ = _adb(["shell", "ip", "route"], serial=serial, timeout=8)   # fallback
    m = re.search(r"\bsrc (\d+\.\d+\.\d+\.\d+)", out or "")
    return m.group(1) if m else ""


def adb_connect(addr):
    """`adb connect ip[:port]` (defaults to :5555)."""
    if not have(adb_bin()):
        return {"ok": False, "error": "adb not found (set it in Config / Paths)"}
    addr = (addr or "").strip()
    if not addr:
        return {"ok": False, "error": "no address — enter IP:port"}
    if ":" not in addr:
        addr += ":5555"
    out, err, _ = _adb(["connect", addr], timeout=20)
    msg = ((out or "") + (err or "")).strip()
    low = msg.lower()
    ok = "connected to" in low or "already connected" in low
    res = {"ok": ok, "addr": addr, "out": msg[:300]}
    if not ok:
        res["error"] = msg[:300] or "connect failed"
    return res


def adb_pair(addr, code):
    """`adb pair ip:port code` — Android 11+ Wireless-debugging first-time pairing."""
    if not have(adb_bin()):
        return {"ok": False, "error": "adb not found"}
    addr = (addr or "").strip(); code = (code or "").strip()
    if not addr or not code:
        return {"ok": False, "error": "need the pairing IP:port and the 6-digit code"}
    out, err, _ = _adb(["pair", addr, code], timeout=25)
    msg = ((out or "") + (err or "")).strip()
    ok = "successfully paired" in msg.lower()
    res = {"ok": ok, "out": msg[:300]}
    if not ok:
        res["error"] = msg[:300] or "pair failed"
    return res


def adb_disconnect(addr):
    """`adb disconnect [ip:port]` — drops one Wi-Fi device, or all if blank."""
    if not have(adb_bin()):
        return {"ok": False, "error": "adb not found"}
    addr = (addr or "").strip()
    out, err, rc = _adb(["disconnect"] + ([addr] if addr else []), timeout=10)
    return {"ok": rc == 0, "out": ((out or "") + (err or "")).strip()[:200]}


def adb_tcpip(serial):
    """Flip a USB-connected device to Wi-Fi adb (`tcpip 5555`), then auto-connect
    over its Wi-Fi IP so the cable can be unplugged."""
    if not have(adb_bin()):
        return {"ok": False, "error": "adb not found"}
    if not serial:
        return {"ok": False, "error": "select a USB-connected device first"}
    ip = _device_ip(serial)
    out, err, rc = _adb(["tcpip", "5555"], serial=serial, timeout=15)
    msg = ((out or "") + (err or "")).strip()
    if rc != 0 and "restarting" not in msg.lower():
        return {"ok": False, "error": msg[:200] or "adb tcpip failed"}
    time.sleep(1.2)                      # let adbd restart in TCP mode
    if not ip:
        return {"ok": True, "ip": "", "hint": "couldn't read the device Wi-Fi IP — "
                "enter IP:5555 manually (Settings ▸ About ▸ Status)"}
    return {"ok": True, "ip": ip, "addr": ip + ":5555", "connect": adb_connect(ip + ":5555")}


# ---- QR-code pairing (Android 11+ "Pair device with QR code") ----------------
# Same scheme Android Studio uses: we render a QR encoding
# `WIFI:T:ADB;S:<name>;P:<password>;;`. The phone (Developer options ▸ Wireless
# debugging ▸ Pair with QR code) scans it and advertises an `_adb-tls-pairing._tcp`
# mDNS service whose instance name == <name>; we discover it via `adb mdns
# services`, run `adb pair <addr> <password>`, then connect to the device's
# `_adb-tls-connect._tcp`. No typing an IP/code by hand.
_QR = {"name": None, "password": None, "paired": False, "host": None}


def _qr_svg(payload):
    """Render the pairing payload as an inline SVG QR (segno — pure-python, bundled
    with the sidecar). Returns '' if segno isn't installed (dev runs from source)."""
    try:
        import io, segno
        buf = io.BytesIO()
        segno.make(payload, error="m").save(buf, kind="svg", scale=6, border=2,
                                            dark="#0a0a0a", light="#ffffff")
        return buf.getvalue().decode("utf-8")
    except Exception:
        return ""


def _mdns_services():
    """Parse `adb mdns services` → [{name, type, addr}] for the _adb-tls-* services."""
    out, _, _ = _adb(["mdns", "services"], timeout=8)
    rows = []
    for line in (out or "").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1].startswith("_adb-tls"):
            rows.append({"name": parts[0], "type": parts[1], "addr": parts[2]})
    return rows


def adb_qr_start():
    """Begin a QR pairing session: returns the QR (SVG) to display + the payload."""
    if not have(adb_bin()):
        return {"ok": False, "error": "adb not found (set it in Config / Paths)"}
    name = "AppPreview-" + secrets.token_hex(3)
    password = "%06d" % secrets.randbelow(1000000)
    _QR.update(name=name, password=password, paired=False, host=None)
    payload = "WIFI:T:ADB;S:%s;P:%s;;" % (name, password)
    svg = _qr_svg(payload)
    return {"ok": True, "payload": payload, "name": name, "svg": svg, "needSegno": not svg,
            "hint": "Trên điện thoại: Developer options → Wireless debugging → "
                    "Pair device with QR code → quét mã này."}


def adb_qr_poll():
    """Poll mDNS for the scanned pairing service → pair → connect. The frontend
    calls this on a timer after showing the QR until it returns connected:true."""
    if not _QR.get("name"):
        return {"ok": False, "error": "no QR session — press the QR button again"}
    svcs = _mdns_services()
    if not _QR["paired"]:
        pairing = next((s for s in svcs if "pairing" in s["type"] and s["name"] == _QR["name"]), None)
        if not pairing:
            return {"ok": True, "waiting": "scan"}        # phone hasn't scanned yet
        out, err, _ = _adb(["pair", pairing["addr"], _QR["password"]], timeout=25)
        msg = ((out or "") + (err or "")).strip()
        if "successfully paired" not in msg.lower():
            return {"ok": False, "error": msg[:200] or "pair failed"}
        _QR["paired"] = True
        _QR["host"] = pairing["addr"].rsplit(":", 1)[0]   # match the connect svc by host
    # Paired → connect to the device's connect service (same host if we can tell).
    conn = next((s for s in svcs if "connect" in s["type"]
                 and (not _QR["host"] or s["addr"].startswith(_QR["host"] + ":"))), None)
    if not conn:
        return {"ok": True, "paired": True, "waiting": "connect"}   # adbd re-advertising
    c = adb_connect(conn["addr"])
    res = {"ok": bool(c.get("ok")), "paired": True, "connected": bool(c.get("ok")), "addr": conn.get("addr")}
    if not c.get("ok"):
        res["error"] = c.get("error")
    return res


# ---- Android emulator (AVD) management -------------------------------------
# A booted emulator shows up in `adb devices` as emulator-NNNN and is then
# driven by the exact same mirror/control code as a physical phone. These two
# helpers only handle listing the available AVDs and booting one.

def _running_avds():
    """Names of AVDs that are currently booted (matched via `adb emu avd name`)."""
    names = set()
    if not have(adb_bin()):
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
    if not have(emulator_bin()):
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
    return {"ok": True, "avds": avds, "emulator": emulator_bin()}


def emu_launch(name):
    """Boot an AVD headfully; it then appears in adb devices for mirror/control."""
    if not have(emulator_bin()):
        return {"ok": False, "error": "emulator binary not found"}
    if not name:
        return {"ok": False, "error": "no AVD name"}
    proc = _AVD_PROCS.get(name)
    if proc and proc.poll() is None:
        return {"ok": True, "already": True}
    _AVD_PROCS[name] = subprocess.Popen(
        [emulator_bin(), "-avd", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"ok": True, "launched": True}


def run_emulator(args, timeout=15):
    """Run the emulator CLI (separate from _adb since it's a different binary)."""
    p = subprocess.run([emulator_bin()] + list(args), capture_output=True, timeout=timeout)
    return p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), p.returncode
