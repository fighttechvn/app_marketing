"""iOS (real iPhone/iPad) — control via WebDriverAgent (WDA) over a USB tunnel.

iOS has no adb-equivalent: WDA is the standard input-injection agent. We forward
WDA's HTTP (8100) + MJPEG (9100) ports off-device with `iproxy` (libimobiledevice)
and translate gestures to WDA's HTTP API. Requires WDA already RUNNING on the
device (Xcode or go-ios launch). NOTE: WDA gesture coords are logical POINTS
(window/size), not screenshot pixels — the frontend maps clicks via the points
size reported by status().
"""
import os, re, json, glob, time, base64, shutil, tempfile, subprocess, urllib.request
from .util import find_bin, have, run
from . import remote   # when a remote Mac runner is connected, simctl/xcodebuild run there

IPROXY = find_bin("iproxy", "IPROXY_BIN")
IDEVICE_ID = find_bin("idevice_id", "IDEVICE_ID_BIN")
IDEVICEINFO = find_bin("ideviceinfo", "IDEVICEINFO_BIN")
GO_IOS = find_bin("ios", "GO_IOS_BIN")     # danielpaulus/go-ios (device list / fallback)
XCODEBUILD = shutil.which("xcodebuild") or "/usr/bin/xcodebuild"
XCRUN = shutil.which("xcrun") or "/usr/bin/xcrun"   # simctl lives behind xcrun
_RUNWDA = {"udid": None, "proc": None}     # the WDA runner (xcodebuild) we started
_RUNWDA_LOG = os.path.join(tempfile.gettempdir(), "sp-runwda.log")
_SIM_SET = set()                           # known simulator UDIDs (refreshed by _sim_list)


# ---- local vs remote dispatch -------------------------------------------------
# When a Mac runner is connected (remote.active()), the macOS-only commands
# (simctl/xcodebuild) run on the Mac over SSH, and WDA's HTTP/MJPEG ports reach
# the Mac through the SSH tunnel (so the 127.0.0.1 WDA code below is unchanged).
def _rmt():        return remote.active()
def _xcrun():      return "xcrun" if _rmt() else XCRUN
def _xcodebuild(): return "xcodebuild" if _rmt() else XCODEBUILD
def _host_run(argv, timeout=20):
    return remote.run(argv, timeout) if _rmt() else run(argv, timeout)


def _have_xcrun():
    if _rmt():
        try: return _host_run([_xcrun(), "--version"], timeout=10)[2] == 0
        except Exception: return False
    return have(XCRUN) and have(XCODEBUILD)


def _sim_list():
    """Available iOS simulators via `simctl`. Returns [{udid,name,os,state}] and
    refreshes the cached UDID set so the rest of the module can tell sim from real."""
    if not _have_xcrun():
        return []
    try:
        out, _, rc = _host_run([_xcrun(), "simctl", "list", "devices", "available", "--json"], timeout=20)
        devices = json.loads(out or "{}").get("devices", {}) if rc == 0 else {}
    except Exception:
        return []
    sims = []
    for runtime, devs in devices.items():
        if "iOS" not in runtime:
            continue
        m = re.search(r"iOS[.-](\d+)[.-](\d+)", runtime)
        osv = (m.group(1) + "." + m.group(2)) if m else ""
        for d in devs:
            if not d.get("isAvailable", True):
                continue
            sims.append({"udid": d["udid"], "name": d["name"], "os": osv, "state": d.get("state", "")})
    _SIM_SET.clear()
    _SIM_SET.update(s["udid"] for s in sims)
    return sims


def _is_sim(udid):
    """True if udid is an iOS simulator (its WDA listens on the host directly)."""
    if not udid:
        return False
    if udid in _SIM_SET:
        return True
    _sim_list()           # populate the cache on a cold lookup
    return udid in _SIM_SET


def _sim_info(udid):
    for s in _sim_list():
        if s["udid"] == udid:
            return s
    return {}


def _sim_boot(udid):
    """Boot a simulator (idempotent) and bring Simulator.app to the front."""
    _host_run([_xcrun(), "simctl", "boot", udid], timeout=40)   # rc!=0 if already booted — fine
    if _rmt():
        try: _host_run(["open", "-a", "Simulator"], timeout=10)
        except Exception: pass
    else:
        subprocess.Popen(["open", "-a", "Simulator"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _wda_project():
    """Locate a WebDriverAgent.xcodeproj — Appium's xcuitest driver bundles one."""
    p = os.environ.get("WDA_PROJECT")
    if p and os.path.exists(p):
        return p
    home = os.path.expanduser("~")
    for pat in (home + "/.appium/node_modules/**/appium-webdriveragent/WebDriverAgent.xcodeproj",
                home + "/**/appium-webdriveragent/WebDriverAgent.xcodeproj"):
        hits = glob.glob(pat, recursive=True)
        if hits:
            return hits[0]
    return ""


def _wda_team(udid):
    """Signing team: $WDA_TEAM_ID, else auto-detected from the installed WDA app."""
    if os.environ.get("WDA_TEAM_ID"):
        return os.environ["WDA_TEAM_ID"]
    if _go_ok():
        try:
            out, _, _ = run([GO_IOS, "apps", "--udid=" + udid], timeout=20)
            m = re.search(r'"application-identifier":"([A-Z0-9]+)\.com\.facebook\.WebDriverAgentRunner', out)
            if m:
                return m.group(1)
        except Exception:
            pass
    return ""


def _wda_ready():
    try:
        return bool(_wda("GET", "/status", timeout=3).get("value", {}).get("ready"))
    except Exception:
        return False


def _runwda_err():
    """Last meaningful error line from the WDA runner log (xcodebuild or go-ios)."""
    try:
        lines = [l for l in open(_RUNWDA_LOG, encoding="utf-8", errors="replace").read().splitlines() if l.strip()]
    except Exception:
        return ""
    for l in reversed(lines):
        low = l.lower()
        if '"level":"error"' in low or "error:" in low or "failed" in low or "no profiles" in low:
            try:
                return json.loads(l).get("error", l)[:240]
            except Exception:
                return l[:240]
    return lines[-1][:240] if lines else ""
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
    """Resolve to the given udid, or fall back to the first device/simulator."""
    if udid:
        return udid
    if _rmt():
        sims = _sim_list()
        return sims[0]["udid"] if sims else None
    return (_ios_list() or [None])[0]


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
    sims = _sim_list()
    if _rmt():
        # remote Mac: only its simulators (no USB device passthrough over SSH).
        return {"ok": True, "remote": True, "host": remote.status().get("host"),
                "iproxy": False, "goios": False, "tunnel": True, "simctl": _have_xcrun(),
                "devices": [],
                "sims": [{"udid": s["udid"], "name": s["name"], "ios": s["os"],
                          "state": s["state"], "kind": "simulator"} for s in sims]}
    return {"ok": True, "iproxy": have(IPROXY), "goios": _go_ok(), "tunnel": _tunnel_running(),
            "simctl": _have_xcrun(),
            "devices": [{"udid": u, "name": _ios_info(u, "DeviceName") or u,
                         "ios": _ios_info(u, "ProductVersion"), "kind": "device"}
                        for u in _ios_list()],
            "sims": [{"udid": s["udid"], "name": s["name"], "ios": s["os"],
                      "state": s["state"], "kind": "simulator"} for s in sims]}


def _wda_project_remote():
    """Locate a WebDriverAgent.xcodeproj on the Mac (Appium's xcuitest bundles one).
    Pass a plain command string (no login shell) so profile banners can't pollute
    the result, and accept it only if it really is a .xcodeproj path."""
    cmd = ('p="${WDA_PROJECT:-}"; if [ -n "$p" ] && [ -e "$p" ]; then echo "$p"; exit; fi; '
           'find "$HOME/.appium" -type d -name WebDriverAgent.xcodeproj 2>/dev/null | head -1')
    try:
        out, _, _ = remote.run(cmd, timeout=25)
    except Exception:
        return ""
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    line = lines[-1] if lines else ""
    return line if line.endswith("WebDriverAgent.xcodeproj") else ""


def _launch_remote(udid):
    """Boot the Mac's simulator and (if a WDA project exists) launch WebDriverAgent
    on the Mac via a detached `xcodebuild test`. WDA's 8100/9100 reach us through
    the SSH tunnel, so taps + live MJPEG work once it's up."""
    udid = _ios_default(udid)
    if not udid:
        return {"ok": False, "error": "no simulator on the Mac"}
    _sim_boot(udid)                       # booted → simctl screenshot mirror works immediately
    if _wda_ready():
        return {"ok": True, "running": True, "sim": True, "remote": True}
    proj = _wda_project_remote()
    if not proj:
        return {"ok": True, "running": False, "sim": True, "noinput": True, "remote": True,
                "hint": "Simulator booted on the Mac — live screen works. Install Appium's WDA on the "
                        "Mac (`appium driver install xcuitest`) for tap/swipe control."}
    cmd = ("nohup xcodebuild -project %s -scheme WebDriverAgentRunner "
           "-destination 'platform=iOS Simulator,id=%s' CODE_SIGNING_ALLOWED=NO test "
           "> /tmp/sp-runwda.log 2>&1 & echo started") % (remote._q(proj), udid)
    try:
        remote.run(cmd, timeout=20)
    except Exception as e:
        return {"ok": False, "error": "failed to start WebDriverAgent on the Mac",
                "detail": str(e)[:160], "remote": True}
    return {"ok": True, "running": False, "launching": True, "sim": True, "remote": True,
            "hint": "Building & launching WebDriverAgent on the Mac… first time ~1–3 min, then it connects."}


def ios_launch(udid):
    """One-click WebDriverAgent launcher via `xcodebuild test` (Apple's own path —
    works on iOS 18 where go-ios `runwda` can't, and needs NO sudo tunnel).
    Returns immediately; the frontend polls /api/wda/status until it's up. First
    build can take 1–3 min, subsequent launches ~15s (DerivedData is cached)."""
    if _rmt():
        return _launch_remote(udid)
    udid = _ios_default(udid)
    if not udid:
        return {"ok": False, "error": "no device connected"}
    sim = _is_sim(udid)
    if sim:
        _sim_boot(udid)                       # boot it now → screenshot mirror works immediately
    # already up (e.g. launched from Xcode / a previous click)?
    _ios_tunnel(udid)
    if _wda_ready():
        return {"ok": True, "running": True, "sim": sim}
    proj = _wda_project()
    if not proj:
        if sim:                               # simulator still mirrors via simctl screenshots
            return {"ok": True, "running": False, "sim": True, "noinput": True,
                    "hint": "Simulator booted — live screen works. Install Appium's WDA "
                            "(`appium driver install xcuitest`) for tap/swipe control."}
        return {"ok": False, "error": "WebDriverAgent.xcodeproj not found",
                "hint": "Install Appium's driver (`appium driver install xcuitest`) or set WDA_PROJECT."}
    # (re)launch the runner if ours isn't alive
    p = _RUNWDA["proc"]
    if not (p and p.poll() is None):
        if sim:
            cmd = [XCODEBUILD, "-project", proj, "-scheme", "WebDriverAgentRunner",
                   "-destination", "platform=iOS Simulator,id=" + udid,
                   "CODE_SIGNING_ALLOWED=NO", "test"]
        else:
            team = _wda_team(udid)
            cmd = [XCODEBUILD, "-project", proj, "-scheme", "WebDriverAgentRunner",
                   "-destination", "id=" + udid, "-allowProvisioningUpdates", "CODE_SIGNING_ALLOWED=YES"]
            if team:
                cmd.append("DEVELOPMENT_TEAM=" + team)
            cmd.append("test")
        logf = open(_RUNWDA_LOG, "wb")
        _RUNWDA["proc"] = subprocess.Popen(cmd, stdout=logf, stderr=logf,
                                           start_new_session=True, cwd=os.path.dirname(proj))
        _RUNWDA["udid"] = udid
    time.sleep(3)
    proc = _RUNWDA["proc"]
    if proc and proc.poll() is not None:      # died immediately → signing/build error
        return {"ok": False, "error": "WebDriverAgent failed to launch", "sim": sim,
                "detail": _runwda_err(),
                "hint": ("Build failed — open WebDriverAgent.xcodeproj in Xcode once." if sim else
                         "Signing failed — set WDA_TEAM_ID, or open WebDriverAgent.xcodeproj in "
                         "Xcode once and pick a team. Make sure the iPhone is unlocked & trusted.")}
    return {"ok": True, "running": False, "launching": True, "sim": sim,
            "team": ("" if sim else _wda_team(udid)), "project": proj,
            "hint": "Building & launching WebDriverAgent… first time ~1–3 min, then it connects."}


def _ios_tunnel(udid):
    """Ensure an iproxy USB tunnel (forwards 8100+9100) for `udid`; restart on change.
    Simulators need no tunnel — their WDA binds 127.0.0.1:8100 on the host directly —
    so we must also TEAR DOWN any device tunnel, or :8100 would still point at the
    physical device's WDA and the sim would mirror the wrong screen."""
    if _rmt():
        return   # the SSH port-forward (remote.py) already maps Mac 8100/9100 → here
    if _is_sim(udid):
        cur = _IPROXY["proc"]
        if cur and cur.poll() is None:   # transitioning away from a real device
            cur.terminate()
            _IPROXY["udid"] = None
            _IPROXY["proc"] = None
            _WDA_SID.pop(udid, None)     # drop a stale session that pointed at the device's WDA
        return
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
        # tuned for a smooth live mirror over USB (high framerate, good quality)
        _wda("POST", "/session/%s/appium/settings" % sid,
             {"settings": {"mjpegServerFramerate": 30, "mjpegServerScreenshotQuality": 60,
                           "mjpegScalingFactor": 100}})
    except Exception:
        pass
    return sid


def ios_status(udid):
    udid = _ios_default(udid)
    sim = _is_sim(udid)
    info = _sim_info(udid) if sim else {}
    name = info.get("name") if sim else _ios_info(udid, "DeviceName")
    osv = info.get("os") if sim else _ios_info(udid, "ProductVersion")
    _ios_tunnel(udid)
    try:
        _wda("GET", "/status", timeout=5)
    except Exception as e:
        booted = (info.get("state") == "Booted") if sim else False
        return {"ok": True, "running": False, "sim": sim, "booted": booted,
                "name": name, "ios": osv,
                "hint": ("Simulator — live screen works; press ▶ Start WDA for tap/swipe control." if sim
                         else "WDA not reachable on :8100 — launch WebDriverAgent on the device"),
                "detail": str(e)[:140]}
    sid = _wda_session(udid)
    size = {}
    try:
        size = _wda("GET", "/session/%s/window/size" % sid).get("value", {})
    except Exception:
        pass
    return {"ok": True, "running": True, "sim": sim, "size": size, "name": name, "ios": osv}


def ios_screen(udid):
    udid = _ios_default(udid)
    _ios_tunnel(udid)
    try:
        b64 = _wda("GET", "/screenshot", timeout=15).get("value")
        if b64:
            return base64.b64decode(b64)
        raise RuntimeError("no screenshot from WDA")
    except Exception:
        if not _is_sim(udid):
            raise
    # simulator without WDA → simctl still gives us the picture (no input though).
    if _rmt():
        # take the shot on the Mac, then pull the bytes back over SFTP.
        rpath = "/tmp/sp-sim-%s.png" % (udid[:8])
        _, err, rc = remote.run([_xcrun(), "simctl", "io", udid, "screenshot", "--type=png", rpath], timeout=20)
        if rc != 0:
            raise RuntimeError(err.strip() or "remote simctl screenshot failed")
        data = remote.read_file(rpath)
        if not data:
            raise RuntimeError("remote simctl screenshot empty")
        return data
    # Write to a temp file (newer simctl treats "-" as a literal path, not stdout).
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        _, err, rc = run([XCRUN, "simctl", "io", udid, "screenshot", "--type=png", path], timeout=15)
        if rc != 0:
            raise RuntimeError(err.strip() or "simctl screenshot failed")
        with open(path, "rb") as f:
            data = f.read()
    finally:
        try: os.remove(path)
        except OSError: pass
    if not data:
        raise RuntimeError("simctl screenshot empty")
    return data


def ios_sim_boot(udid):
    """Boot a simulator for a screenshot-only mirror (no WDA build)."""
    if not _have_xcrun():
        return {"ok": False, "error": "xcrun/simctl not found — install Xcode"}
    if not udid:
        return {"ok": False, "error": "no simulator selected"}
    _sim_boot(udid)
    return {"ok": True, "booted": True}


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
