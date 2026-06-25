"""iOS (real iPhone/iPad) — control via WebDriverAgent (WDA) over a USB tunnel.

iOS has no adb-equivalent: WDA is the standard input-injection agent. We forward
WDA's HTTP (8100) + MJPEG (9100) ports off-device with `iproxy` (libimobiledevice)
and translate gestures to WDA's HTTP API. Requires WDA already RUNNING on the
device (Xcode or go-ios launch). NOTE: WDA gesture coords are logical POINTS
(window/size), not screenshot pixels — the frontend maps clicks via the points
size reported by status().
"""
import os, json, time, base64, tempfile, subprocess, urllib.request
from .util import find_bin, have, run

IPROXY = find_bin("iproxy", "IPROXY_BIN")
IDEVICE_ID = find_bin("idevice_id", "IDEVICE_ID_BIN")
IDEVICEINFO = find_bin("ideviceinfo", "IDEVICEINFO_BIN")
GO_IOS = find_bin("ios", "GO_IOS_BIN")     # danielpaulus/go-ios — launches WDA
_RUNWDA = {"udid": None, "proc": None}     # the `ios runwda` process we started
_RUNWDA_LOG = os.path.join(tempfile.gettempdir(), "sp-runwda.log")


def _runwda_err():
    """Last meaningful error line from the runwda log (for diagnostics)."""
    try:
        lines = [l for l in open(_RUNWDA_LOG, encoding="utf-8", errors="replace").read().splitlines() if l.strip()]
    except Exception:
        return ""
    for l in reversed(lines):
        if '"level":"ERROR"' in l or "error" in l.lower():
            try:
                return json.loads(l).get("error", l)[:200]
            except Exception:
                return l[:200]
    return lines[-1][:200] if lines else ""
WDA_HTTP_LOCAL, WDA_MJPEG_LOCAL = 8100, 9100
WDA_BASE = "http://127.0.0.1:%d" % WDA_HTTP_LOCAL
WDA_MJPEG = "http://127.0.0.1:%d" % WDA_MJPEG_LOCAL
_IPROXY = {"udid": None, "proc": None}    # one active USB tunnel at a time
_WDA_SID = {}                             # udid -> cached WDA sessionId
WDA_BUTTONS = {"home": "home", "volup": "volumeUp", "voldown": "volumeDown"}


def _ios_list():
    if not have(IDEVICE_ID):
        return []
    out, _, _ = run([IDEVICE_ID, "-l"], timeout=10)
    return [u.strip() for u in out.splitlines() if u.strip()]


def _ios_info(udid, key):
    if not udid or not have(IDEVICEINFO):
        return ""
    out, _, rc = run([IDEVICEINFO, "-u", udid, "-k", key], timeout=8)
    return out.strip() if rc == 0 else ""


def _ios_default(udid):
    """Resolve to the given udid, or fall back to the first connected device."""
    return udid or (_ios_list() or [None])[0]


def _go_ok():
    return have(GO_IOS)


def _tunnel_running():
    """True if a go-ios RemoteXPC tunnel (iOS 17+) is already up."""
    if not _go_ok():
        return False
    try:
        out, _, rc = run([GO_IOS, "tunnel", "ls"], timeout=8)
        out = out.strip()
        return rc == 0 and out not in ("", "[]", "null")
    except Exception:
        return False


def ios_devices():
    return {"ok": True, "iproxy": have(IPROXY), "goios": _go_ok(), "tunnel": _tunnel_running(),
            "devices": [{"udid": u, "name": _ios_info(u, "DeviceName") or u,
                         "ios": _ios_info(u, "ProductVersion")} for u in _ios_list()]}


def ios_launch(udid):
    """One-click WebDriverAgent launcher via go-ios. Automates everything that
    doesn't need root; the iOS 17+ tunnel needs `sudo`, which a localhost web
    button can't supply — so when the tunnel is down we return the one command
    for the user to run, then they click again."""
    udid = _ios_default(udid)
    if not udid:
        return {"ok": False, "error": "no device connected"}
    if not _go_ok():
        return {"ok": False, "need": "go-ios", "cmd": "npm install -g go-ios",
                "hint": "Install go-ios (the `ios` CLI), then click Start WDA again."}
    if not _tunnel_running():
        return {"ok": False, "needsTunnel": True, "cmd": "sudo ios tunnel start",
                "hint": "Start the iOS 17+ USB tunnel once (needs your password, keep it open), "
                        "then click Start WDA again."}
    # tunnel is up — (re)launch the WDA runner if ours isn't alive, logging output
    # so a device-side failure (Developer Mode off / locked / untrusted) is surfaced.
    p = _RUNWDA["proc"]
    if not (p and p.poll() is None):
        logf = open(_RUNWDA_LOG, "wb")
        _RUNWDA["proc"] = subprocess.Popen([GO_IOS, "runwda", "--udid=" + udid],
                                           stdout=logf, stderr=logf, start_new_session=True)
        _RUNWDA["udid"] = udid
    DEV_HINT = ("WDA couldn't launch on the device. On the iPhone: unlock it, enable "
                "Settings ▸ Privacy & Security ▸ Developer Mode, and trust the developer app "
                "(Settings ▸ General ▸ VPN & Device Management). Or run WebDriverAgentRunner "
                "once from Xcode.")
    # wait (bounded) for WDA's HTTP server to answer through the iproxy tunnel
    for _ in range(20):
        proc = _RUNWDA["proc"]
        if proc and proc.poll() is not None:      # runwda exited → read why and stop early
            return {"ok": False, "error": "WebDriverAgent failed to launch",
                    "detail": _runwda_err(), "hint": DEV_HINT}
        try:
            _ios_tunnel(udid)
            if _wda("GET", "/status", timeout=3):
                return {"ok": True, "running": True}
        except Exception:
            pass
        time.sleep(1)
    return {"ok": True, "running": False, "launching": True,
            "hint": "WebDriverAgent is starting — give it a few seconds, then press ⟳."}


def _ios_tunnel(udid):
    """Ensure an iproxy USB tunnel (forwards 8100+9100) for `udid`; restart on change."""
    if not have(IPROXY):
        raise RuntimeError("iproxy not found (brew install libimobiledevice)")
    cur = _IPROXY["proc"]
    if _IPROXY["udid"] == udid and cur and cur.poll() is None:
        return
    if cur and cur.poll() is None:
        cur.terminate()
    cmd = [IPROXY, "%d:%d" % (WDA_HTTP_LOCAL, WDA_HTTP_LOCAL),
           "%d:%d" % (WDA_MJPEG_LOCAL, WDA_MJPEG_LOCAL)]
    if udid:
        cmd += ["-u", udid]
    _IPROXY["proc"] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _IPROXY["udid"] = udid
    time.sleep(0.6)   # let the listeners bind before the first request


def _wda(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(WDA_BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def _wda_session(udid):
    """Return a live WDA sessionId, creating one (+ MJPEG settings) if needed."""
    sid = _WDA_SID.get(udid)
    if sid:
        try:
            if _wda("GET", "/status", timeout=5).get("sessionId"):
                return sid
        except Exception:
            pass
    res = _wda("POST", "/session", {"capabilities": {"alwaysMatch": {}, "firstMatch": [{}]}})
    sid = res.get("sessionId") or (res.get("value") or {}).get("sessionId")
    _WDA_SID[udid] = sid
    try:
        _wda("POST", "/session/%s/appium/settings" % sid,
             {"settings": {"mjpegServerFramerate": 20, "mjpegServerScreenshotQuality": 25,
                           "mjpegScalingFactor": 100}})
    except Exception:
        pass
    return sid


def ios_status(udid):
    udid = _ios_default(udid)
    _ios_tunnel(udid)
    try:
        _wda("GET", "/status", timeout=5)
    except Exception as e:
        return {"ok": True, "running": False, "name": _ios_info(udid, "DeviceName"),
                "ios": _ios_info(udid, "ProductVersion"),
                "hint": "WDA not reachable on :8100 — launch WebDriverAgent on the device",
                "detail": str(e)[:140]}
    sid = _wda_session(udid)
    size = {}
    try:
        size = _wda("GET", "/session/%s/window/size" % sid).get("value", {})
    except Exception:
        pass
    return {"ok": True, "running": True, "size": size,
            "name": _ios_info(udid, "DeviceName"), "ios": _ios_info(udid, "ProductVersion")}


def ios_screen(udid):
    udid = _ios_default(udid)
    _ios_tunnel(udid)
    b64 = _wda("GET", "/screenshot", timeout=15).get("value")
    if not b64:
        raise RuntimeError("no screenshot from WDA")
    return base64.b64decode(b64)


def ios_mjpeg_open(udid):
    """Ensure the tunnel and open WDA's MJPEG stream; returns the urllib response
    so the HTTP layer can relay it to the browser <img>."""
    _ios_tunnel(_ios_default(udid))
    return urllib.request.urlopen(WDA_MJPEG + "/", timeout=10)


def ios_input(body):
    udid = _ios_default(body.get("udid") or None)
    _ios_tunnel(udid)
    act = body.get("action")
    if act in ("lock", "unlock"):
        _wda("POST", "/wda/" + act, {})
        return {"ok": True}
    sid = _wda_session(udid)
    if act == "tap":
        _wda("POST", "/session/%s/wda/tap/0" % sid, {"x": float(body["x"]), "y": float(body["y"])})
    elif act == "swipe":
        _wda("POST", "/session/%s/wda/dragfromtoforduration" % sid,
             {"fromX": float(body["x1"]), "fromY": float(body["y1"]),
              "toX": float(body["x2"]), "toY": float(body["y2"]),
              "duration": max(float(body.get("ms", 150)) / 1000.0, 0.05)})
    elif act == "button":
        name = WDA_BUTTONS.get(str(body.get("key", "")).lower())
        if not name:
            return {"ok": False, "error": "unknown button %s" % body.get("key")}
        _wda("POST", "/session/%s/wda/pressButton" % sid, {"name": name})
    elif act == "text":
        _wda("POST", "/session/%s/wda/keys" % sid, {"value": list(str(body.get("text", "")))})
    else:
        return {"ok": False, "error": "unknown action %s" % act}
    return {"ok": True}
